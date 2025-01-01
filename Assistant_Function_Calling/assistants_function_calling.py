from openai import OpenAI
from typing_extensions import override
from openai import AssistantEventHandler

client = OpenAI()


# 1. Define functions
# In this example, we'll create a weather assistant and define two functions, 
# get_current_temperature and get_rain_probability, as tools that the Assistant can call.  
assistant = client.beta.assistants.create(
instructions="You are a weather bot. Use the provided functions to answer questions.",
model="gpt-4o",
tools=[
  {
    "type": "function",
    "function": {
      "name": "get_current_temperature",
      "description": "Get the current temperature for a specific location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "The city and state, e.g., San Francisco, CA"
          },
          "unit": {
            "type": "string",
            "enum": ["Celsius", "Fahrenheit"],
            "description": "The temperature unit to use. Infer this from the user's location."
          }
        },
        "required": ["location", "unit"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "get_rain_probability",
      "description": "Get the probability of rain for a specific location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "The city and state, e.g., San Francisco, CA"
          }
        },
        "required": ["location"]
      }
    }
  }
]
)


# 2. Create a Thread and add Messages
thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
thread_id=thread.id,
role="user",
content="What's the weather in San Francisco today and the likelihood it'll rain?",
)


# 3. Initiate a Run
"""
When you initiate a Run on a Thread containing a user Message that triggers one or more functions, 
the Run will enter a pending status. After it processes, the run will enter a requires_action state 
which you can verify by checking the Run’s status. This indicates that you need to run tools and submit 
their outputs to the Assistant to continue Run execution. In our case, we will see two tool_calls, 
which indicates that the user query resulted in parallel function calling.
"""
class EventHandler(AssistantEventHandler):
  @override
  def on_event(self, event):
    # Retrieve events that are denoted with 'requires_action'
    # since these will have our tool_calls
    if event.event == 'thread.run.requires_action':
      run_id = event.data.id  # Retrieve the run ID from the event data
      self.handle_requires_action(event.data, run_id)

  def handle_requires_action(self, data, run_id):
    tool_outputs = []
      
    for tool in data.required_action.submit_tool_outputs.tool_calls:
      if tool.function.name == "get_current_temperature":
        tool_outputs.append({"tool_call_id": tool.id, "output": "57"})
      elif tool.function.name == "get_rain_probability":
        tool_outputs.append({"tool_call_id": tool.id, "output": "0.06"})
      
    # Submit all tool_outputs at the same time
    self.submit_tool_outputs(tool_outputs, run_id)

  def submit_tool_outputs(self, tool_outputs, run_id):
    # Use the submit_tool_outputs_stream helper
    with client.beta.threads.runs.submit_tool_outputs_stream(
      thread_id=self.current_run.thread_id,
      run_id=self.current_run.id,
      tool_outputs=tool_outputs,
      event_handler=EventHandler(),
    ) as stream:
      for text in stream.text_deltas:
        print(text, end="", flush=True)
      print()


with client.beta.threads.runs.stream(
thread_id=thread.id,
assistant_id=assistant.id,
event_handler=EventHandler()
) as stream:
  stream.until_done()