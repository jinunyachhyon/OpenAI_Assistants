from openai import OpenAI

client = OpenAI()


# Upload a file with an "assistants" purpose
file = client.files.create(
file=open("sample_data.csv", "rb"),
purpose='assistants'
)


# Create an assistant using the file ID
assistant = client.beta.assistants.create(
name="Data Visualizer",
description="Generates data visualizations based on trends in CSV files.",
instructions="You are a data visualizer. When asked to visualize, write and run code to generate visualizations.",
model="gpt-4o",
tools=[{"type": "code_interpreter"}],
tool_resources={
  "code_interpreter": {
    "file_ids": [file.id]
  }
}
)


# Create a thread
thread = client.beta.threads.create(
messages=[
  {
    "role": "user",
    "content": "Create data visualization for trend in the uploaded CSV file.",
    "attachments": [
      {
        "file_id": file.id,
        "tools": [{"type": "code_interpreter"}]
      }
    ]
  }
]
)


# Create a Run
run = client.beta.threads.runs.create_and_poll(
thread_id=thread.id,
assistant_id=assistant.id,
)

if run.status == 'completed': 
    messages = client.beta.threads.messages.list(
    thread_id=thread.id
    )
    print(messages)
else:
    print(run.status)