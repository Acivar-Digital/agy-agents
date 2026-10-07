"""
Tests for agy-agents MCP Server
===============================

Verifies:
1. Pydantic V2 contract schema validation and constraints.
2. FastMCP tool registration count and schemas.
3. Sovereign tool execution: prompt preparation, prompt discovery,
   gateway health inspection, refactoring, and async job tracking.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

import mcp_server
from mcp_server import (
    GatewayStatusOutput,
    PromptPreparationInput,
    PromptPreparationOutput,
    RefactorInput,
    RefactorOutput,
    ResearchStatusInput,
    ResearchStatusOutput,
    StartResearchInput,
    StartResearchOutput,
    check_gateway_health,
    get_research_status,
    list_research_prompts,
    mcp,
    prepare_research_prompt,
    refactor_code,
    start_research,
)
from refactor import RefactorExecutionResult


class TestMCPContracts(unittest.TestCase):
    """Verifies Pydantic V2 model schema enforcement and validation rules."""

    def test_prompt_preparation_input_valid(self):
        inp = PromptPreparationInput(
            topic="Quantum Computing", prompt_stem="quantum_stem"
        )
        self.assertEqual(inp.topic, "Quantum Computing")
        self.assertEqual(inp.prompt_stem, "quantum_stem")
        self.assertIsNone(inp.custom_rubric)

    def test_prompt_preparation_input_rejections(self):
        # min_length=3 for topic
        with self.assertRaises(ValidationError):
            PromptPreparationInput(topic="QC")

        # extra="forbid"
        with self.assertRaises(ValidationError):
            PromptPreparationInput(topic="Valid Topic", unexpected_field="boom")

    def test_start_research_input_validation(self):
        inp = StartResearchInput(
            prompt_stem_or_topic="Direction_of_JPY", timeout_seconds=300.0
        )
        self.assertEqual(inp.prompt_stem_or_topic, "Direction_of_JPY")
        self.assertEqual(inp.timeout_seconds, 300.0)

        # timeout must be > 0
        with self.assertRaises(ValidationError):
            StartResearchInput(
                prompt_stem_or_topic="Direction_of_JPY", timeout_seconds=0.0
            )

        # extra fields forbidden
        with self.assertRaises(ValidationError):
            StartResearchInput(prompt_stem_or_topic="Valid", extra_arg=123)

    def test_research_status_input_validation(self):
        inp = ResearchStatusInput(job_id="job_12345678")
        self.assertEqual(inp.job_id, "job_12345678")

        # empty job_id rejected
        with self.assertRaises(ValidationError):
            ResearchStatusInput(job_id="")

    def test_refactor_input_validation(self):
        inp = RefactorInput(code="def hello():\n    print('world')\n")
        self.assertEqual(inp.filename, "target.py")
        self.assertIsNone(inp.instructions)

        # code shorter than 5 chars rejected
        with self.assertRaises(ValidationError):
            RefactorInput(code="def")


class TestMCPToolRegistration(unittest.TestCase):
    """Verifies FastMCP server metadata and tool exports."""

    def test_server_metadata_and_tool_count(self):
        self.assertEqual(mcp.name, "agy-agents")

        async def _check_tools():
            tools = await mcp.list_tools()
            tool_names = {t.name for t in tools}
            expected = {
                "prepare_research_prompt",
                "start_research",
                "get_research_status",
                "refactor_code",
                "list_research_prompts",
                "check_gateway_health",
            }
            self.assertEqual(expected, tool_names)
            self.assertEqual(len(tools), 6)

        asyncio.run(_check_tools())


class TestMCPToolsExecution(unittest.TestCase):
    """Tests execution of the 6 sovereign MCP tools."""

    def setUp(self):
        self.test_stem = "_test_tmp_stem_for_mcp"
        self.test_prompt_file = mcp_server.PROMPTS_DIR / f"{self.test_stem}.md"

    def tearDown(self):
        if self.test_prompt_file.exists():
            self.test_prompt_file.unlink()

    def test_prepare_research_prompt(self):
        res = prepare_research_prompt(
            topic="Next-generation Optical Interconnects in AI Clusters",
            prompt_stem=self.test_stem,
            custom_rubric="Focus strictly on Co-Packaged Optics (CPO) vs Pluggable transceivers.",
        )
        self.assertIn("Research Prompt Prepared", res)
        self.assertIn(self.test_stem, res)
        self.assertIn("nohup uv run python deep-research/deep-research.py", res)
        self.assertTrue(self.test_prompt_file.exists())

        content = self.test_prompt_file.read_text(encoding="utf-8")
        self.assertIn("Next-generation Optical Interconnects", content)
        self.assertIn("Co-Packaged Optics", content)
        self.assertIn("CITI INSTITUTIONAL DEEP RESEARCH PROTOCOL", content)

    def test_list_research_prompts(self):
        res = list_research_prompts()
        self.assertIn("### Available Research Prompts", res)
        self.assertIn("| Stem | Type | Target Objective |", res)
        self.assertIn("Direction_of_JPY", res)
        self.assertIn("AI_Infrastructure_Mid_2026", res)

    def test_check_gateway_health(self):
        res = check_gateway_health()
        self.assertIn("Gateway Health", res)
        self.assertIn("Active Provider:", res)
        self.assertIn("Target URL:", res)

    @patch("mcp_server.execute_refactor")
    def test_refactor_code_mocked(self, mock_exec):
        mock_exec.return_value = RefactorExecutionResult(
            status="completed",
            provider="literouter",
            refactored_code="def calculate_total(price: float, tax: float) -> float:\n    return price * (1.0 + tax)\n",
            elapsed_seconds=1.23,
            raw_response={"steps": []},
        )

        res = refactor_code(
            code="def calculate_total(price, tax):\n    return price * (1.0 + tax)\n",
            filename="pricing.py",
            instructions="Add strict type annotations",
        )
        self.assertIn("Refactoring Completed", res)
        self.assertIn("pricing.py", res)
        self.assertIn("Valid Python Syntax", res)
        self.assertIn("def calculate_total(price: float", res)

    def test_async_research_lifecycle(self):
        # 1. Start research with dynamic stem
        tmp_stem = "_test_lifecycle_stem"
        res_start = start_research(
            prompt_stem_or_topic="Autonomous Mobile Robotics in Warehouse Logistics",
            prompt_stem=tmp_stem,
            timeout_seconds=10.0,
        )
        self.assertIn("Research Dispatched", res_start)
        self.assertIn("get_research_status", res_start)

        # Extract job_id
        import re

        match = re.search(r"job_[a-f0-9]{8}", res_start)
        self.assertIsNotNone(match)
        job_id = match.group(0)

        # 2. Poll research status
        res_status = get_research_status(job_id=job_id)
        self.assertIn(job_id, res_status)
        self.assertTrue(
            "running" in res_status
            or "completed" in res_status
            or "failed" in res_status
        )

        # 3. Test non-existent job ID
        res_invalid = get_research_status(job_id="job_nonexistent_999")
        self.assertIn("not found", res_invalid)

        # Clean up created files
        job_file = mcp_server.JOBS_DIR / f"{job_id}.json"
        if job_file.exists():
            job_file.unlink()
        prompt_file = mcp_server.PROMPTS_DIR / f"{tmp_stem}.md"
        if prompt_file.exists():
            prompt_file.unlink()

    def test_dual_network_app_streamable_http_and_sse(self):
        from starlette.testclient import TestClient

        app = mcp_server.create_network_app(mcp)
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        with TestClient(app) as client:
            # 1. Streamable HTTP POST to /sse (used by omp via opencode.json type: remote)
            resp_sse_post = client.post("/sse", json=init_payload, headers=headers)
            self.assertEqual(resp_sse_post.status_code, 200)
            self.assertIn("agy-agents", resp_sse_post.text)

            # 2. Streamable HTTP POST to /mcp
            resp_mcp_post = client.post("/mcp", json=init_payload, headers=headers)
            self.assertEqual(resp_mcp_post.status_code, 200)
            self.assertIn("agy-agents", resp_mcp_post.text)

            # 3. HEAD probe on /sse
            resp_sse_head = client.head("/sse")
            self.assertEqual(resp_sse_head.status_code, 200)

            # 4. Static /reports/{filename} HTTP pickup & stem-based Markdown delivery
            resp_md = client.get("/reports/Direction_of_JPY_20260729_0826.md")
            self.assertEqual(resp_md.status_code, 200)
            self.assertIn("INSTITUTIONAL DEEP RESEARCH REPORT", resp_md.text)

        res_jpy = get_research_status(job_id="Direction_of_JPY")
        self.assertIn("#### Full Markdown Report", res_jpy)
        self.assertIn(
            "http://agy-agents.lan:7788/reports/Direction_of_JPY_20260729_0826.md",
            res_jpy,
        )


if __name__ == "__main__":
    unittest.main()
