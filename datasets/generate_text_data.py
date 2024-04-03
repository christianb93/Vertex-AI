#
# Generate sentiment analyis test data using an LLM
#

import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os
import json

#
# Prompt template
#
prompt_template = {
    "system" : """
You are a data scientist who is creating test data for a sentiment classification task. Please provide 10 samples
consisting of a sentence and a label describing the sentiment which describes that sentence best. Use the following
labeling scheme:
0 = negative
1 = neutral
2 = positive
Format your output as an array in JSON format with the two fields content (the sentence) and label. Make sure that your
output is pure JSON without any additional characters at the beginning and the end of your response.

Here are a few examples:

[
    {
        "content" : "This is the best day of my entire life, so great to be here",
    "label" : 2
    }
    {
        "content" : "An absolute nightmare, how could this ever happen",
        "label" : 0
    }
    { 
        "content" : "London is the capital of the United Kingdom",
        "label" : 1
    }
]
""",
    "user": "Now please provide 10 samples following this pattern."
    }    




#
# Connect to the Google Vertex AI API
# 
def get_vertex_ai():
    google_project_id = os.getenv("GOOGLE_PROJECT_ID")
    google_region = "us-central1"
    vertexai.init(project = google_project_id, location = google_region)

#
# Run a request against the model. The input is supposed to be in the
# OpenAI messages format, i.e. 
#    messages = [
#            {"role" : "system", "content" : system_prompt},
#            {"role" : "user", "content" : user_prompt},
#        ]       
#
def generate(model_name, messages):
    if model_name == "Google Palm":
        model = vertexai.language_models.TextGenerationModel.from_pretrained("text-bison@002")
        prompt = "\n".join([f"{m['content']}" for m in messages])
        response = model.predict(prompt, temperature = 0.0)
        return response.text
    elif model_name == "Google Gemini":
        model = GenerativeModel("gemini-pro")
        prompt = "\n".join([f"{m['content']}" for m in messages])
        response = model.generate_content(prompt)
        return response.candidates[0].content.parts[0].text   
    else:
        print(f"Model {model_name} not supported")
        exit(1)
    


model_name = "Google Gemini"
target = 100
get_vertex_ai()
documents = []
while len(documents) < target:
    print("Running batch")
    response = generate(model_name, messages = [
        { "role" : "system", "content" : f"{prompt_template['system']}"},
        { "role" : "user", "content" : f"{prompt_template['user']}"},
    ])
    try:
        data = json.loads(response)
        for record in data:
            document = {
                "textContent" : f"{record['content']}",
                "sentimentAnnotation" :  
                        { 
                            "sentiment" : record['label'] ,
                            "sentimentMax" : 2
                        }
            }
            documents.append(document)
    except BaseException as e:
        print("Response is not valid JSON, discarding this batch")
        continue
    print("Batch valid, appending")
    

#
# Write to file, making sure to have linebreaks between records
#
with open("text.jsonl", "w") as out:
    for document in documents:
        json.dump(document, out)
        out.write("\n")
