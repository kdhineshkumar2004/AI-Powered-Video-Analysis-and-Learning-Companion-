import requests
import json

url = "http://127.0.0.1:5000/analyze"
data = {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Replace with your desired YouTube URL
}

response = requests.post(url, json=data)

if response.status_code == 200:
    with open('analysis.pdf', 'wb') as f:
        f.write(response.content)
    print("PDF downloaded successfully!")
else:
    print(f"Error: {response.status_code} - {response.json()}")
