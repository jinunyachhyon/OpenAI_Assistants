from openai import OpenAI

client = OpenAI()

image_data = client.files.content("file-id")
image_data_bytes = image_data.read()

with open("./visualization.png", "wb") as file:
  file.write(image_data_bytes)