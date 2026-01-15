import json
import os
import time
import google.generativeai as genai

# 1. SETUP: Enter your API Key from Google AI Studio
os.environ["GOOGLE_API_KEY"] = "YOUR_AI_STUDIO_API_KEY"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Initialize the model with Google Search capabilities
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    tools=[{"google_search": {}}]
)

FILE_PATH = 'ingredients_catalog.json'

def get_density_data(ingredient_name):
    """Asks Gemini to find density via Google Search."""
    prompt = f"""
    Find the standard density for baking ingredient: "{ingredient_name}".
    I need the weight of 1 standard US Cup.
    Return ONLY a raw JSON object with these keys:
    "density_volume_value" (always 1.0),
    "density_volume_unit" (always "cup"),
    "density_weight_value" (the number),
    "density_weight_unit" (either "g" or "oz").
    If you cannot find a reliable value, return null.
    """
    try:
        response = model.generate_content(prompt)
        # Extract the JSON block from the response
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"Error fetching {ingredient_name}: {e}")
        return None

def process_catalog():
    # Load your file
    with open(FILE_PATH, 'r') as f:
        data = json.load(f)

    ingredients = data.get('ingredients', [])
    updated_count = 0

    for item in ingredients:
        # Check if density data is missing
        if "density_weight_value" not in item or item["density_weight_value"] is None:
            print(f"Searching for: {item['display_name']}...")

            new_data = get_density_data(item['display_name'])

            if new_data and new_data.get("density_weight_value"):
                item.update(new_data)
                updated_count += 1
                print(f"  ✅ Found: {new_data['density_weight_value']} {new_data['density_weight_unit']}")

                # Save after every successful find to persist progress
                with open(FILE_PATH, 'w') as f:
                    json.dump(data, f, indent=2)

            # Small delay to respect API rate limits
            time.sleep(2)

    print(f"\nFinished! Updated {updated_count} items.")

if __name__ == "__main__":
    process_catalog()
