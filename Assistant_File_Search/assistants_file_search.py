from openai import OpenAI
from typing_extensions import override
from openai import AssistantEventHandler, OpenAI

client = OpenAI()

################ Step-1 ################
# Create a new Assistant with File Search Enabled
assistant = client.beta.assistants.create(
name="Financial Analyst Assistant",
instructions="You are an expert financial analyst. Use you knowledge base to answer questions about audited financial statements.",
model="gpt-4o",
tools=[{"type": "file_search"}],
)


################ Step-2: Upload files and add them to a Vector Store ################
# Create a vector store caled "Financial Statements"
vector_store = client.beta.vector_stores.create(name="Financial Statements")

# Ready the files for upload to OpenAI
file_paths = ["appl_10K.pdf"]
file_streams = [open(path, "rb") for path in file_paths]

# Use the upload and poll SDK helper to upload the files, add them to the vector store,
# and poll the status of the file batch for completion.
file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
vector_store_id=vector_store.id, files=file_streams
)

# You can print the status and the file counts of the batch to see the result of this operation.
print("File add to VectorStore Status: ", file_batch.status)
print("File Count in VectorStore: ", file_batch.file_counts)


################ Step-3 ################
# Update the assistant to use the new Vector Store
assistant = client.beta.assistants.update(
assistant_id=assistant.id,
tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)


################ Step-4: Create a thread ################
"""
You can also attach files as Message attachments on your thread. 
Doing so will create another vector_store associated with the thread, 
or, if there is already a vector store attached to this thread, 
attach the new files to the existing thread vector store. 
When you create a Run on this thread, the file search tool will query 
both the vector_store from your assistant and the vector_store on the thread.
"""
# Upload the user provided file to OpenAI 
message_file = client.files.create(
file=open("alphabet_10K.pdf", "rb"), purpose="assistants"
)

# Create a thread and attach the file to the message
thread = client.beta.threads.create(
messages=[
  {
    "role": "user",
    "content": "What are the key revenue trends mentioned in this report for Alphabet as of December 31, 2017?",
    # Attach the new file to the message. --> Automatically create and/or add to thread vector store.
    "attachments": [
      { "file_id": message_file.id, "tools": [{"type": "file_search"}] }
    ],
  }
]
)

# The thread now has a vector store with that file in its tool resources.
print("Thread Details:\n", thread.tool_resources.file_search)


################ Step-5: Create a run and check the output ################
print("\nAssistant Reply:")

class EventHandler(AssistantEventHandler):
  @override
  def on_text_created(self, text) -> None:
      print(f"\nassistant > ", end="", flush=True)

  @override
  def on_tool_call_created(self, tool_call):
      print(f"\nassistant > {tool_call.type}\n", flush=True)

  @override
  def on_message_done(self, message) -> None:
      # print a citation to the file searched
      message_content = message.content[0].text
      annotations = message_content.annotations
      citations = []
      for index, annotation in enumerate(annotations):
          message_content.value = message_content.value.replace(
              annotation.text, f"[{index}]"
          )
          if file_citation := getattr(annotation, "file_citation", None):
              cited_file = client.files.retrieve(file_citation.file_id)
              citations.append(f"[{index}] {cited_file.filename}")

      print(message_content.value)
      print("\n".join(citations))


# Then, we use the stream SDK helper
# with the EventHandler class to create the Run
# and stream the response.
# Note: Your new assistant will query both attached vector stores (one containing appl_10K.pdf, and the other containing alphabet_10K.pdf) 
# and return this result from alphabet_10K.pdf.
with client.beta.threads.runs.stream(
  thread_id=thread.id,
  assistant_id=assistant.id,
  instructions="Please address the user as Jane Doe. The user has a premium account.",
  event_handler=EventHandler(),
) as stream:
  stream.until_done()


