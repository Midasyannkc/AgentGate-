package agentgate

test_allowed_tool_for_agent {
	allow with input as {"agent": "agent-demo-1", "tool": "get_weather"}
}

test_denied_tool_not_in_allowlist {
	not allow with input as {"agent": "agent-demo-2", "tool": "list_files"}
}

test_denied_unknown_agent {
	not allow with input as {"agent": "agent-nonexistent", "tool": "get_weather"}
}

test_rate_limit_lookup {
	rate_limit_per_minute == 30 with input as {"agent": "agent-demo-1"}
}
