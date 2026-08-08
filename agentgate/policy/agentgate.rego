package agentgate

import future.keywords.in

default allow = false

# An agent may call a tool only if that exact tool is in its allowed_tools
# list in data.json. No wildcard grants — every tool an agent can reach has
# to be listed explicitly.
allow {
	some agent
	agent := data.agents[_]
	agent.id == input.agent
	input.tool in agent.allowed_tools
}

# Exposed separately so the gateway can look up an agent's configured rate
# limit without re-implementing the lookup logic on the gateway side.
rate_limit_per_minute = limit {
	some agent
	agent := data.agents[_]
	agent.id == input.agent
	limit := agent.rate_limit_per_minute
}
