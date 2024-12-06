import csv
import json
import os
from datetime import datetime
from models import RecyclingResult

def classify_product(description, image_data=None, openai_client=None):
    print("Starting product classification...")
    
    system_prompt = """You are an expert in beauty product recycling classification.
    Analyze the product and respond ONLY with a valid JSON object (no additional text or markdown).
    Format your entire response as a JSON object like this:
    {
      "components": [
        {
          "component_name": "string",
          "material": "string",
          "disposal_category": "PACT|CURBSIDE RECYCLING|TRASH",
          "classification_explanation": "string"
        }
      ]
    }
    
    Based on the following mapping, classify each component:

    PACT:
    - Plastic bottles & jars (6 fl oz or smaller)
    - Plastic + aluminum squeezable tubes
    - Ceramic + porcelain containers
    - Colored glass bottles + jars
    - Caps + closures
    - Pumps + dispensers
    - Droppers + applicators
    - Compacts + palettes
    - Lipstick/lip gloss tubes + applicators
    - Mascara tubes + wands
    - Plastic pencil components for eye/brow/lip liner
    - Toothpaste tubes
    - Dental floss containers
    - Silicone containers

    CURBSIDE RECYCLING:
    - Plastic containers #1, 2 & 5 (larger than 6 fl oz)
    - Stainless steel
    - Aluminum
    - Cardboard
    - Paper
    - Glass bottles + jars

    TRASH:
    - Plastic containers #3, #4, #6, and #7 (when larger than 2"x2" or 6 fl oz)
    - Broken glass
    - Dental floss
    - Aerosol cans
    - Sponges + brushes
    - Single-use wipes
    - Plastic + foil safety seals
    - Plastic bag + wrappers
    - Plastic with foil/metal inlay
    - Nail polish + remover
    - Toothbrushes

    Analyze the product and provide detailed recycling information in JSON format with the following fields:
    - component_name: name of the product component
    - weight_in_kg: estimated weight in kilograms
    - component_material: material type (include plastic grade if applicable)
    - disposal_category: one of [PACT, CURBSIDE RECYCLING, TRASH]
    - disposal_category_explanation: detailed explanation including size considerations and material composition
    - overall_explanation: comprehensive explanation of the entire product's recycling classification

    Return the response as a JSON object with a 'components' array containing the individual component details and an 'overall_explanation' field."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze this beauty product: {description}"}
    ]

    if image_data:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": f"Analyze this beauty product: {description}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]}
        ]

    if not openai_client:
        raise ValueError("OpenAI client is not initialized")

    try:
        # Validate input
        if not description:
            raise ValueError("Product description is required")

        # Make API call
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4-vision-preview",  # Using vision model for image analysis
                messages=messages,
                max_tokens=1000,
                temperature=0
            )
            
            # Parse response
            content = response.choices[0].message.content
            print("Raw API response:", content)
            
            result = json.loads(content)
            print("Parsed result:", result)
            
            if not isinstance(result, dict) or 'components' not in result:
                raise ValueError("Invalid response format: missing 'components' array")
                
        except json.JSONDecodeError as e:
            print("Failed to parse JSON response:", content)
            raise ValueError(f"Invalid JSON response from API: {str(e)}")
        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            raise ValueError(f"Failed to get response from OpenAI: {str(e)}")

        # Process components
        processed_components = []
        for component in result.get('components', []):
            try:
                processed_component = {
                    'component_name': component.get('component_name', 'Unknown'),
                    'material': component.get('component_material', ''),
                    'disposal_category': component.get('disposal_category', 'TRASH'),
                    'classification_explanation': component.get('disposal_category_explanation', '')
                }
                processed_components.append(processed_component)
            except (TypeError, ValueError) as e:
                continue  # Skip invalid components
            
        return processed_components
        
    except ValueError as e:
        raise Exception(f"Validation error: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to classify product: {str(e)}")

def generate_csv():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recycling_results_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'product_name',
            'component_name',
            'material',
            'disposal_category',
            'classification_explanation'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Get only the most recent classification result from Elasticsearch
        result = RecyclingResult.get_latest()
        
        if result:
            try:
                components = json.loads(result['classification_result'])
                if isinstance(components, list):
                    for component in components:
                        row = {
                            'product_name': result['product_description'],
                            'component_name': component.get('component_name', ''),
                            'material': component.get('material', ''),
                            'disposal_category': component.get('disposal_category', ''),
                            'classification_explanation': component.get('classification_explanation', '')
                        }
                        writer.writerow(row)
            except (json.JSONDecodeError, AttributeError) as e:
                pass
    
    return filename
