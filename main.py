from openai import OpenAI

import os
import json
import requests
from bs4 import BeautifulSoup

from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Load the OpenAI API key from an environment variable

def load_memory():
    """
    Load the memory from a file to maintain continuity.
    If the file is empty or does not exist, return an empty list.
    """
    try:
        with open("memory.json", "r") as file:
            # Try to load the JSON data
            try:
                return json.load(file)
            except json.JSONDecodeError:
                # If JSON is empty or invalid, return an empty list
                return []
    except FileNotFoundError:
        # If the file doesn't exist, return an empty list
        return []


def save_memory(new_entry, article_summary):
    """
    Append the new entry and the article summary to the memory file.
    """
    try:
        memory = load_memory()  # Load existing memory
        new_entry['article_summary'] = article_summary  # Add the article summary to the entry
        memory.append(new_entry)  # Append the new entry
        with open("memory.json", "w") as file:
            json.dump(memory, file)
    except Exception as e:
        print(f"Error during saving memory: {e}")

def perform_search(query):
    """
    Perform a web search using a given query and return the results.
    """
    print(f"Performing search for query: {query}")  # Debugging print

    # Ensure API key and CX are set
    api_key = os.getenv("YOUR_API_KEY")
    cx = os.getenv("YOUR_CX")

    if not api_key or not cx:
        print("API key or CX is not set. Please check your environment variables.")
        return []

    # Perform the search
    try:
        params = {'key': api_key, 'cx': cx, 'q': query, 'num': 5}
        response = requests.get('https://www.googleapis.com/customsearch/v1', params=params)

        if response.status_code == 200:
            search_results = response.json().get('items', [])
            print(f"Search successful. Number of results: {len(search_results)}")  # Debugging print
            return search_results
        else:
            print(f"Search failed with status code {response.status_code}. Response: {response.text}")  # Debugging print
            return []
    except Exception as e:
        print(f"Exception occurred during search: {e}")
        return []



import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

def scrape_website_content(url):
    """
    Scrape the main content from the given URL in a safer way.
    """
    print(f"Attempting to scrape content from {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    try:
        response = requests.get(url, headers=headers, timeout=10)  # Adding headers and a timeout
        print(f"Response status code: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            text = ' '.join([para.get_text(strip=True) for para in paragraphs])
            print(f"Scraped text length: {len(text)}")
            return text[:2000]  # Limiting character count
        else:
            return "Unable to fetch content due to non-200 status code."

    except RequestException as e:
        print(f"Error during scraping: {e}")
        return f"Error during scraping: {e}"



def summarize_with_openai(content, sensory_input):
    """
    This function uses OpenAI to generate a summary of the provided content.
    """
    response = client.completions.create(model="text-davinci-003",
    prompt="Given the user input: '{sensory_input}', Summarize the following content, focusing on the main points and the author's argument:\n\n" + content,
    max_tokens=350)
    return response.choices[0].text.strip()


def summarize_search_results(search_results):
    summary = []
    for result in search_results[:3]:  # Limiting to top 3 results for brevity
        title = result.get('title')
        link = result.get('link')
        snippet = result.get('snippet')
        
        summary_entry = f"Title: {title}, Snippet: {snippet}, URL: {link}"
        summary.append(summary_entry)

    return " | ".join(summary)

def combined_processing(initial_input, current_input, memory):
    """
    Processes the given current input description, considering past decisions stored in memory
    and the initial input for context.
    """
    memory_summary = " ".join([f"Previous situation: '{m['current_input']}' led to decision: '{m['decision']}'." for m in memory])
    prompt = (f"Given the initial input: '{initial_input}', and the current input: '{current_input}', "
              "along with these past decisions: {memory_summary}, "
              "provide a very short response structured as follows: "
              "Processed Input: [input], Decision: [decision], Execution Plan: [plan]. "
              "Include 'search for [query]' in the plan if more information is needed.")

    messages = [
        {"role": "system", "content": "You are an AI designed to process sensory input and make decisions."},
        {"role": "user", "content": prompt}
    ]

    completion = client.chat.completions.create(
        model="gpt-4-0613",
        messages=messages
    )

    response = completion.choices[0].message.content.strip()
    # Extracting processed input, decision, and execution plan from response
    if "Processed Input:" in response and "Decision:" in response and "Execution Plan:" in response:
        processed_input = response.split("Processed Input:")[1].split("Decision:")[0].strip()
        decision = response.split("Decision:")[1].split("Execution Plan:")[0].strip()
        execution_plan = response.split("Execution Plan:")[1].strip()
    else:
        return "Error", "Error", "Error"

    return processed_input, decision, execution_plan


import re

def extract_search_query(execution_plan):
    """
    Extracts a search query from the execution plan using regular expressions.
    """
    match = re.search(r"search for '([^']+)'", execution_plan.lower())
    if match:
        return match.group(1)  # Returns the query found
    else:
        return None  # No query found

def main():
    memory = load_memory()
    print("Welcome to the AI decision-making bot. Please describe your initial situation.")

    initial_input = input("Initial situation: ")
    current_input = initial_input
    previous_execution_plan = None
    repeat_count = 0
    article_summary = ""
    scraped_urls = set()  # Set to keep track of scraped URLs

    while True:
        processed_input, decision, execution_plan = combined_processing(initial_input, current_input, memory)

        if decision == "Error":
            print("There was an error processing the input. Please try again.")
            break

        print(f"AI Decision: {decision}")
        if execution_plan:
            print(f"Execution Plan: {execution_plan}")

        if execution_plan == previous_execution_plan and repeat_count > 1:
            print("Repeated execution plan detected. Please provide a different input.")
            break
        else:
            repeat_count = 0 if execution_plan != previous_execution_plan else repeat_count + 1
            previous_execution_plan = execution_plan

        search_query = extract_search_query(execution_plan)
        if search_query:
            search_results = perform_search(search_query)
            for result in search_results:
                url = result.get('link')
                if url not in scraped_urls:  # Check if the URL has not been scraped before
                    scraped_content = scrape_website_content(url)
                    if scraped_content and not scraped_content.startswith("Error"):
                        summarized_content = summarize_with_openai(scraped_content, current_input)
                        article_summary = summarized_content
                        current_input = summarized_content
                        scraped_urls.add(url)  # Add the URL to the set of scraped URLs
                        break
            else:
                current_input = "No successful scrape"
                article_summary = ""

        elif decision.lower() == 'stop':
            print("AI decision-making process has been stopped.")
            break
        else:
            current_input = decision

        # Saving the initial input, current decision data, and article summary to memory
        save_memory({
            'initial_input': initial_input,
            'current_input': current_input,
            'decision': decision,
            'execution_plan': execution_plan
        }, article_summary)

if __name__ == "__main__":
    main()
