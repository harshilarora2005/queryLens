import google.generativeai as genai

genai.configure(api_key="AIzaSyAAYfSRzMozvRaLXxqi4k1dYBUO03POwno")

for m in genai.list_models():
    print(m.name)