# Content for item 0

```markdown
[Skip to content](https://langchain-ai.github.io/langgraph/how-tos/stream-values/#how-to-stream-full-state-of-your-graph)

[Download Notebook](https://langchain-ai.github.io/langgraph/how-tos/stream-values/stream-values.ipynb "Download Notebook")

# How to stream full state of your graph [¶](https://langchain-ai.github.io/langgraph/how-tos/stream-values/\#how-to-stream-full-state-of-your-graph)

LangGraph supports multiple streaming modes. The main ones are:

- `values`: This streaming mode streams back values of the graph. This is the **full state of the graph** after each node is called.
- `updates`: This streaming mode streams back updates to the graph. This is the **update to the state of the graph** after each node is called.

This guide covers `stream_mode="values"`.

## Setup [¶](https://langchain-ai.github.io/langgraph/how-tos/stream-values/\#setup)

First, let's install the required packages and set our API keys

In \[1\]:

Copied!

```
%%capture --no-stderr
%pip install -U langgraph langchain-openai langchain-community

```

%%capture --no-stderr
%pip install -U langgraph langchain-openai langchain-community

In \[ \]:

Copied!

```
import getpass
import os

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")

```

import getpass
import os

def \_set\_env(var: str):
if not os.environ.get(var):
os.environ\[var\] = getpass.getpass(f"{var}: ")

\_set\_env("OPENAI\_API\_KEY")

Set up [LangSmith](https://smith.langchain.com) for LangGraph development

Sign up for LangSmith to quickly spot issues and improve the performance of your LangGraph projects. LangSmith lets you use trace data to debug, test, and monitor your LLM apps built with LangGraph — read more about how to get started [here](https://docs.smith.langchain.com).


## Define the graph [¶](https://langchain-ai.github.io/langgraph/how-tos/stream-values/\#define-the-graph)

We'll be using a simple ReAct agent for this guide.

In \[3\]:

Copied!

```
from typing import Literal
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.runnables import ConfigurableField
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

@tool
def get_weather(city: Literal["nyc", "sf"]):
    """Use this to get weather information."""
    if city == "nyc":
        return "It might be cloudy in nyc"
    elif city == "sf":
        return "It's always sunny in sf"
    else:
        raise AssertionError("Unknown city")

tools = [get_weather]

model = ChatOpenAI(model_name="gpt-4o", temperature=0)
graph = create_react_agent(model, tools)

```

from typing import Literal
from langchain\_community.tools.tavily\_search import TavilySearchResults
from langchain\_core.runnables import ConfigurableField
from langchain\_core.tools import tool
from langchain\_openai import ChatOpenAI
from langgraph.prebuilt import create\_react\_agent

@tool
def get\_weather(city: Literal\["nyc", "sf"\]):
"""Use this to get weather information."""
if city == "nyc":
return "It might be cloudy in nyc"
elif city == "sf":
return "It's always sunny in sf"
else:
raise AssertionError("Unknown city")

tools = \[get\_weather\]

model = ChatOpenAI(model\_name="gpt-4o", temperature=0)
graph = create\_react\_agent(model, tools)

## Stream values [¶](https://langchain-ai.github.io/langgraph/how-tos/stream-values/\#stream-values)

In \[4\]:

Copied!

```
inputs = {"messages": [("human", "what's the weather in sf")]}
async for chunk in graph.astream(inputs, stream_mode="values"):
    chunk["messages"][-1].pretty_print()

```

inputs = {"messages": \[("human", "what's the weather in sf")\]}
async for chunk in graph.astream(inputs, stream\_mode="values"):
chunk\["messages"\]\[-1\].pretty\_print()

```
================================ Human Message =================================

what's the weather in sf
================================== Ai Message ==================================
Tool Calls:
  get_weather (call_61VvIzqVGtyxcXi0z6knZkjZ)
 Call ID: call_61VvIzqVGtyxcXi0z6knZkjZ
  Args:
    city: sf
================================= Tool Message =================================
Name: get_weather

It's always sunny in sf
================================== Ai Message ==================================

The weather in San Francisco is currently sunny.

```

If we want to just get the final result, we can use the same method and just keep track of the last value we received

In \[5\]:

Copied!

```
inputs = {"messages": [("human", "what's the weather in sf")]}
async for chunk in graph.astream(inputs, stream_mode="values"):
    final_result = chunk

```

inputs = {"messages": \[("human", "what's the weather in sf")\]}
async for chunk in graph.astream(inputs, stream\_mode="values"):
final\_result = chunk

In \[6\]:

Copied!

```
final_result

```

final\_result

Out\[6\]:

```
{'messages': [HumanMessage(content="what's the weather in sf", id='54b39b6f-054b-4306-980b-86905e48a6bc'),\
  AIMessage(content='', additional_kwargs={'tool_calls': [{'id': 'call_avoKnK8reERzTUSxrN9cgFxY', 'function': {'arguments': '{"city":"sf"}', 'name': 'get_weather'}, 'type': 'function'}]}, response_metadata={'token_usage': {'completion_tokens': 14, 'prompt_tokens': 57, 'total_tokens': 71}, 'model_name': 'gpt-4o-2024-05-13', 'system_fingerprint': 'fp_5e6c71d4a8', 'finish_reason': 'tool_calls', 'logprobs': None}, id='run-f2f43c89-2c96-45f4-975c-2d0f22d0d2d1-0', tool_calls=[{'name': 'get_weather', 'args': {'city': 'sf'}, 'id': 'call_avoKnK8reERzTUSxrN9cgFxY'}], usage_metadata={'input_tokens': 57, 'output_tokens': 14, 'total_tokens': 71}),\
  ToolMessage(content="It's always sunny in sf", name='get_weather', id='fc18a798-c7b2-4f73-84fa-8ffdffb6ddcb', tool_call_id='call_avoKnK8reERzTUSxrN9cgFxY'),\
  AIMessage(content='The weather in San Francisco is currently sunny. Enjoy the sunshine!', response_metadata={'token_usage': {'completion_tokens': 14, 'prompt_tokens': 84, 'total_tokens': 98}, 'model_name': 'gpt-4o-2024-05-13', 'system_fingerprint': 'fp_5e6c71d4a8', 'finish_reason': 'stop', 'logprobs': None}, id='run-21418147-da8e-4738-a076-239377397c40-0', usage_metadata={'input_tokens': 84, 'output_tokens': 14, 'total_tokens': 98})]}
```

In \[7\]:

Copied!

```
final_result["messages"][-1].pretty_print()

```

final\_result\["messages"\]\[-1\].pretty\_print()

```
================================== Ai Message ==================================

The weather in San Francisco is currently sunny. Enjoy the sunshine!

```

## Comments

Back to top
```

----
