#!/usr/bin/env python3
"""
Analytics Dashboard Generator with Chat Mode

Generates comprehensive analytics dashboards using MCP and LLMs.

Features:
- Real-time data from multiple platforms via MCP
  - Umami (web analytics)
  - Google Search Console (search performance)
  - YouTube (video analytics)
  - Mastodon, Bluesky, LinkedIn, Instagram (social media)
- AI-powered analysis and insights
- Interactive chat mode for asking questions about your data
- Hallucination detection to ensure data accuracy
- Support for multiple AI providers (Cloudflare, Ollama, Gemini)

Usage:
    # Generate dashboard with chat mode (cross-platform)
    uv run run.py --start-date 2025-01-01 --end-date 2025-12-31 --website example.com --chat

    # Generate dashboard without chat
    uv run run.py --start-date 2025-01-01 --end-date 2025-12-31 --website example.com

Chat Mode:
    In chat mode, you can ask questions about your analytics data.
    - Supports multiline input (use Ctrl+D to end input)
    - Type 'quit', 'exit', or 'q' to leave chat mode
    - Data from all configured platforms is automatically injected

Configuration:
    Set credentials in .env file:
    - UMAMI_API_KEY or UMAMI_USERNAME+UMAMI_PASSWORD
    - GSC_SITE_URL (with .gsc_token.json from OAuth)
    - YOUTUBE_API_KEY + YOUTUBE_CHANNEL_ID
    - And more for social platforms
"""

import asyncio
import os
import json
import aiohttp
import warnings
import argparse
from pathlib import Path
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# Suppress specific warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


class AnalyticsDashboard:
    def __init__(self, mcp_server_dir: str, ai_provider: str = "cloudflare"):
        self.mcp_server_dir = mcp_server_dir
        self.ai_provider = ai_provider.lower()
        self.setup_mcp_server()
        self.setup_ai_clients()
        self.session_data = {}  # Store data for chat mode

    def setup_mcp_server(self):
        """Setup MCP server parameters"""
        # Use multi-platform server for cross-platform analytics support
        # This enables Umami, GSC, YouTube, Mastodon, Bluesky, LinkedIn, Instagram
        mcp_server_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "packages",
            "umami-mcp",
            "src",
            "umami_mcp",
            "multi_platform_server.py"
        )

        # Support all platform environment variables
        keys = [
            # Umami
            "UMAMI_URL",
            "UMAMI_API_KEY",
            "UMAMI_USERNAME",
            "UMAMI_PASSWORD",
            "UMAMI_TEAM_ID",
            "UMAMI_TEAM_ACCESS_CODE",
            # GSC
            "GSC_SITE_URL",
            "GSC_TOKEN_FILE",
            # YouTube
            "YOUTUBE_API_KEY",
            "YOUTUBE_CHANNEL_ID",
            # Mastodon
            "MASTODON_INSTANCE",
            "MASTODON_CLIENT_ID",
            "MASTODON_CLIENT_SECRET",
            "MASTODON_ACCESS_TOKEN",
            "MASTODON_ACCOUNT_ID",
            # Bluesky
            "BLUESKY_IDENTIFIER",
            "BLUESKY_PASSWORD",
            # LinkedIn
            "LINKEDIN_CLIENT_ID",
            "LINKEDIN_CLIENT_SECRET",
            "LINKEDIN_ACCESS_TOKEN",
            "LINKEDIN_ORGANIZATION_ID",
            # Instagram
            "INSTAGRAM_ACCESS_TOKEN",
            "INSTAGRAM_BUSINESS_ACCOUNT_ID",
            # Legacy names for backwards compatibility
            "UMAMI_API_URL",
        ]
        env_vars = {k: os.environ[k] for k in keys if k in os.environ}

        # Map legacy UMAMI_API_URL to UMAMI_URL if needed
        if "UMAMI_API_URL" in env_vars and "UMAMI_URL" not in env_vars:
            env_vars["UMAMI_URL"] = env_vars["UMAMI_API_URL"]

        env_vars["TOKENIZERS_PARALLELISM"] = "false"
        env_vars["PYTHONWARNINGS"] = "ignore:resource_tracker:UserWarning"

        self.server_params = StdioServerParameters(
            command="uv",
            args=[
                "run",
                "python",
                mcp_server_path,
            ],
            env=env_vars,
        )

    def setup_ai_clients(self):
        """Setup AI client configurations"""
        self.CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        self.CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
        self.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

    async def call_cloudflare_ai(
        self, prompt: str, model: str = "@cf/meta/llama-3.1-8b-instruct"
    ) -> str:
        """Call Cloudflare Workers AI"""
        if not self.CLOUDFLARE_ACCOUNT_ID or not self.CLOUDFLARE_API_TOKEN:
            raise ValueError(
                "Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN environment variables"
            )

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.CLOUDFLARE_ACCOUNT_ID}/ai/run/{model}"

        headers = {
            "Authorization": f"Bearer {self.CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "temperature": 0.1,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(
                        f"Cloudflare AI error ({response.status}): {error_text}"
                    )

                result = await response.json()
                if not result.get("success"):
                    raise RuntimeError(f"Cloudflare AI API error: {result}")

                return result["result"]["response"].strip()

    async def call_ollama(self, prompt: str, model: str = "llama3.2") -> str:
        """Call Ollama locally"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama",
                "run",
                model,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate(input=prompt.encode())

            if proc.returncode != 0:
                raise RuntimeError(f"Ollama error: {stderr.decode()}")

            return stdout.decode().strip()
        except FileNotFoundError:
            raise RuntimeError("Ollama is not installed or not in PATH")

    async def call_gemini_cli(self, prompt: str) -> str:
        """Call Gemini via CLI"""
        try:
            # The gemini-cli will use authenticated user credentials if available
            # The prompt is passed via stdin
            proc = await asyncio.create_subprocess_exec(
                "npx",
                "@google/gemini-cli",
                "generate",
                "--model",
                "gemini-1.5-flash",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate(input=prompt.encode())

            if proc.returncode != 0:
                raise RuntimeError(f"Gemini-CLI error: {stderr.decode()}")

            return stdout.decode().strip()
        except FileNotFoundError:
            raise RuntimeError(
                "Gemini-CLI (npx @google/gemini-cli) is not installed or not in PATH"
            )


    async def call_gemini_cli(self, prompt: str) -> str:
        """Call Gemini via CLI"""
        try:
            # The gemini-cli takes the prompt via -p flag or stdin
            # Using -p flag is more reliable than stdin
            proc = await asyncio.create_subprocess_exec(
                "npx",
                "@google/gemini-cli",
                "-p",
                prompt,  # Pass prompt directly as parameter
                "--model",
                "gemini-2.5-pro",  # Use the default model
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(f"Gemini-CLI error: {stderr.decode()}")

            response = stdout.decode().strip()

            # The CLI might include extra formatting, so clean it up
            # Remove any ANSI color codes or extra whitespace
            import re

            response = re.sub(r"\x1b\[[0-9;]*m", "", response)  # Remove ANSI codes
            response = response.strip()

            return response

        except FileNotFoundError:
            raise RuntimeError(
                "Gemini-CLI (npx @google/gemini-cli) is not installed or not in PATH"
            )

    async def call_ai_provider(self, prompt: str) -> Tuple[str, str]:
        """Call the specified AI provider"""
        try:
            if self.ai_provider == "cloudflare":
                response = await self.call_cloudflare_ai(prompt)
                return response, "cloudflare"
            elif self.ai_provider == "ollama":
                response = await self.call_ollama(prompt)
                return response, "ollama"
            elif self.ai_provider == "gemini-cli":
                try:
                    response = await self.call_gemini_cli(prompt)
                    return response, "gemini-cli"
                except Exception as cli_error:
                    print(f"Gemini CLI failed: {cli_error}")
                    print("Falling back to Gemini API...")
                    response = await self.call_gemini_api(prompt)
                    return response, "gemini-api"
            else:
                raise ValueError(f"Unsupported AI provider: {self.ai_provider}")

        except Exception as e:
            print(f"Primary AI provider ({self.ai_provider}) failed: {e}")

            # Fallback logic
            if self.ai_provider != "cloudflare":
                try:
                    print("Falling back to Cloudflare...")
                    response = await self.call_cloudflare_ai(prompt)
                    return response, "cloudflare-fallback"
                except Exception as cf_error:
                    print(f"Cloudflare fallback failed: {cf_error}")

            if self.ai_provider != "ollama":
                try:
                    print("Falling back to Ollama...")
                    response = await self.call_ollama(prompt)
                    return response, "ollama-fallback"
                except Exception as ollama_error:
                    print(f"Ollama fallback failed: {ollama_error}")

            raise RuntimeError(f"All AI providers failed. Primary error: {e}")

    def get_website_id_from_domain(
        self, websites_data: list, domain: str
    ) -> Optional[str]:
        """Extract website ID from the websites list based on domain"""
        try:
            if not isinstance(websites_data, list) or len(websites_data) == 0:
                return None

            # Handle the case where websites_data is wrapped in TextContent
            websites_content = websites_data[0]
            if hasattr(websites_content, "text"):
                websites_json = json.loads(websites_content.text)

                # Handle different response formats
                if isinstance(websites_json, dict) and "data" in websites_json:
                    websites_list = websites_json["data"]
                elif isinstance(websites_json, list):
                    websites_list = websites_json
                elif isinstance(websites_json, dict) and "websites" in websites_json:
                    websites_list = websites_json["websites"]
                else:
                    return None

                # Search for matching domain
                for website in websites_list:
                    if website.get("domain") == domain:
                        return website.get("id")
                    if website.get("name") == domain:
                        return website.get("id")

            return None
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"Error parsing websites data: {e}")
            return None

    async def get_real_data_from_mcp(
        self,
        session: ClientSession,
        website_domain: str,
        start_date: str,
        end_date: str,
        timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """Get real data from MCP server with proper error handling"""
        real_data = {
            "website_domain": website_domain,
            "date_range": f"{start_date} to {end_date}",
            "timezone": timezone,
        }

        try:
            # List available tools
            tools_response = await session.list_tools()
            available_tools = [tool.name for tool in tools_response.tools]
            real_data["available_tools"] = available_tools

            # Get website list to find the correct website ID
            if "get_websites" in available_tools:
                try:
                    websites_result = await session.call_tool("get_websites", {})
                    real_data["websites"] = websites_result.content

                    # Extract website ID for the domain
                    website_id = self.get_website_id_from_domain(
                        websites_result.content, website_domain
                    )
                    if website_id:
                        real_data["website_id"] = website_id
                    else:
                        return real_data

                except Exception as e:
                    real_data["websites_error"] = str(e)
                    return real_data

            # Now try other endpoints with the correct website_id and parameters
            website_id = real_data.get("website_id")
            if not website_id:
                print("No website ID available, skipping other API calls")
                return real_data

            # Get website stats with proper parameters
            if "get_stats" in available_tools:
                try:
                    stats_result = await session.call_tool(
                        "get_stats",
                        {
                            "website_id": website_id,
                            "start_at": start_date,
                            "end_at": end_date,
                            "unit": "day",
                            "timezone": timezone,
                        },
                    )
                    real_data["website_stats"] = stats_result.content
                except Exception as e:
                    real_data["stats_error"] = str(e)

            # Get pageview series with proper parameters
            if "get_pageviews" in available_tools:
                try:
                    pageview_result = await session.call_tool(
                        "get_pageviews",
                        {
                            "website_id": website_id,
                            "start_at": start_date,
                            "end_at": end_date,
                            "unit": "day",
                            "timezone": timezone,
                        },
                    )
                    real_data["pageview_series"] = pageview_result.content
                except Exception as e:
                    real_data["pageview_error"] = str(e)

            # Get website metrics with proper parameters
            if "get_metrics" in available_tools:
                try:
                    for metric_type in [
                        "url",
                        "referrer",
                        "browser",
                        "os",
                        "device",
                        "country",
                        "language",
                        "event",
                    ]:
                        try:
                            metrics_result = await session.call_tool(
                                "get_metrics",
                                {
                                    "website_id": website_id,
                                    "start_at": start_date,
                                    "end_at": end_date,
                                    "metric_type": metric_type,
                                    "timezone": timezone,
                                },
                            )
                            real_data[f"metrics_{metric_type}"] = metrics_result.content
                        except Exception:
                            pass
                except Exception as e:
                    real_data["metrics_error"] = str(e)

            # Get UTM metrics if available
            if "get_utm_metrics" in available_tools:
                try:
                    for utm_type in [
                        "utm_source",
                        "utm_medium",
                        "utm_campaign",
                        "utm_content",
                        "utm_term",
                    ]:
                        try:
                            utm_result = await session.call_tool(
                                "get_utm_metrics",
                                {
                                    "website_id": website_id,
                                    "start_at": start_date,
                                    "end_at": end_date,
                                    "utm_type": utm_type,
                                    "timezone": timezone,
                                },
                            )
                            real_data[f"utm_{utm_type}"] = utm_result.content
                        except Exception:
                            pass
                except Exception as e:
                    real_data["utm_metrics_error"] = str(e)

            # Get active visitors
            if "get_active_visitors" in available_tools:
                try:
                    active_result = await session.call_tool(
                        "get_active_visitors", {"website_id": website_id}
                    )
                    real_data["active_visitors"] = active_result.content
                except Exception as e:
                    real_data["active_visitors_error"] = str(e)

        except Exception as e:
            real_data["general_error"] = str(e)

        return real_data

    async def create_validation_prompt(
        self, mcp_prompt: str, real_data: Dict[str, Any]
    ) -> str:
        """Create a comprehensive validation prompt"""
        real_data_str = json.dumps(real_data, indent=2, default=str)

        prompt = f"""You are an expert analytics consultant creating a dashboard based on REAL data from an analytics system.

DASHBOARD CREATION GUIDE:
{mcp_prompt}

ACTUAL DATA FROM ANALYTICS SYSTEM:
{real_data_str}

CRITICAL REQUIREMENTS:
1. ONLY use the real data provided above - NEVER fabricate numbers
2. If data is missing/unavailable, clearly state this and explain why
3. Provide actionable insights based on available data
4. Suggest specific next steps for missing data
5. Create visualizations only for data that actually exists
6. Be transparent about data limitations

ANALYSIS TARGET:
- Website: {real_data.get('website_domain', 'Unknown')}
- Period: {real_data.get('date_range', 'Unknown')}
- Timezone: {real_data.get('timezone', 'Unknown')}

Create a comprehensive dashboard analysis using ONLY the real data provided."""
        return prompt

    async def create_chat_prompt(self, user_question: str) -> str:
        """Create a chat prompt with context from the session data"""
        real_data_str = json.dumps(self.session_data, indent=2, default=str)

        return f"""You are an expert analytics consultant answering questions about website analytics data.

CONTEXT - AVAILABLE DATA:
{real_data_str}

USER QUESTION: {user_question}

GUIDELINES:
1. Answer based ONLY on the real data provided above
2. If the data doesn't contain information to answer the question, say so clearly
3. Provide specific insights and recommendations when possible
4. Suggest what additional data might be needed if the question can't be fully answered
5. Be conversational but professional
6. Refer to specific metrics and time periods from the data when relevant

Answer the user's question about the website analytics:"""

    def detect_hallucinations(self, ai_response: str) -> list:
        """Enhanced hallucination detection"""
        hallucination_indicators = [
            # Common fake numbers
            "1,234,567",
            "45,678",
            "12,345",
            "100,000",
            "50,000",
            # Generic metrics without real data
            "Total pageviews: 1",
            "Unique visitors: 1",
            # Placeholder language
            "fictional",
            "example data",
            "placeholder",
            "sample data",
            "dummy data",
            "test data",
            "mock data",
            # Vague time references without real data
            "peak hours",
            "busy periods",
            "high traffic times",
            # Made-up percentages
            "45% increase",
            "30% bounce rate",
            "25% growth",
        ]

        found_indicators = []
        for indicator in hallucination_indicators:
            if indicator.lower() in ai_response.lower():
                found_indicators.append(indicator)

        return found_indicators

    async def chat_mode(self):
        """Interactive chat mode for asking questions about the data"""
        print(
            f"\n🤖 Entering chat mode using {self.ai_provider.upper()}! Ask questions about your analytics data."
        )
        print("Type 'quit', 'exit', or 'q' to leave chat mode.")
        print("Use Ctrl+D (or Ctrl+Z on Windows) to end multiline input.\n")

        while True:
            try:
                print("\n📊 Your question: ", end="", flush=True)

                # Read multiline input
                lines = []
                try:
                    while True:
                        line = input()
                        # Check for quit command in the input
                        if line.strip().lower() in ["quit", "exit", "q"] and not lines:
                            print("👋 Exiting chat mode. Goodbye!")
                            return
                        lines.append(line)
                except EOFError:
                    # Ctrl+D pressed - end of input
                    pass

                user_input = "\n".join(lines).strip()

                if not user_input:
                    continue

                # Create chat prompt with context
                chat_prompt = await self.create_chat_prompt(user_input)

                # Get AI response
                print(f"\n🤔 Thinking with {self.ai_provider}...")
                ai_response, ai_provider = await self.call_ai_provider(chat_prompt)

                print(f"\n💬 {ai_provider.upper()} Response:")
                print("-" * 50)
                print(ai_response)
                print("-" * 50)

            except KeyboardInterrupt:
                print("\n\n👋 Exiting chat mode. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error in chat: {e}")
                continue

    async def create_dashboard(
        self,
        website_domain: str,
        start_date: str,
        end_date: str,
        timezone: str = "UTC",
        enable_chat: bool = False,
    ):
        """Main method to create dashboard"""
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    print("✅ Connected to MCP server")

                    # Initialize session
                    try:
                        await session.initialize()
                        print("✅ Session initialized")
                    except Exception as init_error:
                        print(f"❌ Initialization error: {init_error}")
                        return

                    # Get real data
                    print(f"\n📊 Getting real data for {website_domain}...")
                    real_data = await self.get_real_data_from_mcp(
                        session, website_domain, start_date, end_date, timezone
                    )

                    # Store data for chat mode
                    self.session_data = real_data

                    # Generate dashboard analysis
                    # Try to use MCP prompts if available, otherwise use built-in prompt
                    mcp_prompt = None
                    try:
                        prompts_response = await session.list_prompts()
                        prompts = [p.name for p in prompts_response.prompts]
                        print(f"📋 Available prompts: {prompts}")

                        if "Create Dashboard" in prompts:
                            dashboard_args = {
                                "Website Name": website_domain,
                                "Start Date (YYYY-MM-DD)": start_date,
                                "End Date (YYYY-MM-DD)": end_date,
                                "Timezone": timezone,
                            }

                            prompt_response = await session.get_prompt(
                                "Create Dashboard", dashboard_args
                            )

                            if prompt_response.messages:
                                message_content = prompt_response.messages[0].content
                                mcp_prompt = getattr(
                                    message_content, "text", str(message_content)
                                )
                    except Exception as prompt_error:
                        print(f"ℹ️  Prompts not available: {prompt_error}")
                        print("   Using built-in analysis instead")

                    # Create analysis prompt (with or without MCP prompt template)
                    if mcp_prompt:
                        validation_prompt = await self.create_validation_prompt(
                            mcp_prompt, real_data
                        )
                    else:
                        # Built-in prompt when MCP prompts aren't available
                        validation_prompt = await self.create_builtin_analysis_prompt(real_data)

                    # Get AI response
                    print(
                        f"\n🤖 Generating dashboard with {self.ai_provider.upper()}..."
                    )
                    ai_response, ai_provider = await self.call_ai_provider(
                        validation_prompt
                    )

                    print(
                        f"\n📈 DASHBOARD ANALYSIS ({ai_provider.upper()}):"
                    )
                    print("=" * 80)
                    print(ai_response)
                    print("=" * 80)

                    # Check for hallucinations
                    hallucination_indicators = self.detect_hallucinations(
                        ai_response
                    )
                    if hallucination_indicators:
                        print(
                            f"\n⚠️  Potential data fabrication detected: {hallucination_indicators}"
                        )
                    else:
                        print(
                            "\n✅ Analysis appears to be based on real data"
                        )

                    # Enter chat mode if enabled
                    if enable_chat:
                        await self.chat_mode()

        except Exception as e:
            print(f"❌ Error in dashboard creation: {e}")
            import traceback

            traceback.print_exc()

    async def create_builtin_analysis_prompt(self, real_data: Dict[str, Any]) -> str:
        """Create a built-in analysis prompt when MCP prompts aren't available"""
        real_data_str = json.dumps(real_data, indent=2, default=str)

        return f"""You are an expert analytics consultant analyzing website analytics data from Umami.

ACTUAL DATA FROM ANALYTICS SYSTEM:
{real_data_str}

CRITICAL REQUIREMENTS:
1. ONLY use the real data provided above - NEVER fabricate numbers
2. If data is missing/unavailable, clearly state this and explain why
3. Provide actionable insights based on available data
4. Suggest specific next steps for missing data
5. Create visualizations only for data that actually exists
6. Be transparent about data limitations

ANALYSIS TARGET:
- Website: {real_data.get('website_domain', 'Unknown')}
- Period: {real_data.get('date_range', 'Unknown')}
- Timezone: {real_data.get('timezone', 'Unknown')}

Provide a comprehensive dashboard analysis using ONLY the real data provided. Include:
1. Traffic summary (pageviews, unique visitors, sessions)
2. Top content (pages and referrers)
3. Geographic analysis if available
4. Device and browser breakdown if available
5. Key insights and recommendations based on the data"""


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Analytics Dashboard Generator")

    parser.add_argument(
        "--mcp-server-dir",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "umami_mcp_server"),
        help="Path to MCP server directory",
    )
    parser.add_argument(
        "--website", default="example.com", help="Website domain to analyze"
    )
    parser.add_argument(
        "--start-date", default="2025-06-01", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", default="2025-07-01", help="End date (YYYY-MM-DD)"
    )
    parser.add_argument("--timezone", default="UTC", help="Timezone for analysis")
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Enable interactive chat mode after generating report",
    )
    parser.add_argument(
        "--ai-provider",
        choices=["cloudflare", "ollama", "gemini-cli"],
        default="gemini-cli",
        help="AI provider to use (default: cloudflare)",
    )

    return parser.parse_args()


async def main():
    """Main function with command-line argument parsing"""
    args = parse_arguments()

    print(f"🚀 Starting Analytics Dashboard")
    print(f"   Website: {args.website}")
    print(f"   Date Range: {args.start_date} to {args.end_date}")
    print(f"   Timezone: {args.timezone}")
    print(f"   AI Provider: {args.ai_provider.upper()}")
    print(f"   Chat Mode: {'Enabled' if args.chat else 'Disabled'}")
    print()

    # Create dashboard
    dashboard = AnalyticsDashboard(args.mcp_server_dir, args.ai_provider)
    await dashboard.create_dashboard(
        args.website, args.start_date, args.end_date, args.timezone, args.chat
    )


if __name__ == "__main__":
    asyncio.run(main())
