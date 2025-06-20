import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
import os
import streamlit as st
from streamlit_chat import message
from google import genai
from google.genai import types
import json
from dotenv import load_dotenv
# Run the neural scraper server with
# uvicorn app:app --reload --host 0.0.0.0 --port 1688

load_dotenv()

class CompanyIntelligencePipeline:
    def __init__(
        self,
        neuscraper_endpoint="http://0.0.0.0:1688/predict/",
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        data_dir="company_data",
    ) -> None:
        self.neuscraper_endpoint = neuscraper_endpoint
        self.gemini_api_key = gemini_api_key
        self.data_dir = data_dir

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        self.gemini_client = genai.Client(api_key=self.gemini_api_key)

    def scrape_yellow_pages(self, search_query, page_limit=1, delay=5):
        all_companies = []

        for page in range(1, page_limit + 1):
            if page == 1:
                url = f"https://www.yellowpages.id/listing/places/?bbox=&d=20&l=&lat=&lon=&q={search_query.replace(' ', '+')}"
            else:
                url = f"https://www.yellowpages.id/listing/places/?bbox=&d=20&l=&lat=&lon=&q={search_query.replace(' ', '+')}&page={page}"

            print(f"Scraping Yellow Pages: {url}")
            response = requests.get(url)

            if response.status_code != 200:
                print(
                    f"Failed to access page {page}. Status code: {response.status_code}"
                )
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("div", class_="cc-content")
            print(f"Found {len(cards)} companies on page {page}")

            for card in cards:
                company = {
                    "name": (
                        card.find("a")["title"]  # type: ignore
                        if card.find("a") and "title" in card.find("a").attrs  # type: ignore
                        else ""
                    ),
                    "url": card.find("a")["href"] if card.find("a") else "",  # type: ignore
                    "address": (
                        card.find("address").get_text(strip=True)  # type: ignore
                        if card.find("address")  # type: ignore
                        else ""
                    ),
                }
                all_companies.append(company)

            time.sleep(delay)

        return all_companies

    def scrape_company_details(self, companies, delay=5):
        detailed_companies = []

        for i, company in enumerate(companies):
            if not company["url"]:
                continue

            print(f"Scraping details for {company['name']} ({i+1}/{len(companies)})")

            try:
                resp = requests.get(company["url"])
                if resp.status_code != 200:
                    print(f"Failed to access company page: {company['url']}")
                    detailed_companies.append(company)
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                sections = soup.find_all("section", attrs={"id": "company_card"})

                for section in sections:
                    company["street_address"] = (
                        section.find(  # type: ignore
                            "span", attrs={"itemprop": "streetAddress"}  # type: ignore
                        ).get_text(
                            strip=True
                        )  # type: ignore
                        if section.find("span", attrs={"itemprop": "streetAddress"})  # type: ignore
                        else ""
                    )
                    company["postal_code"] = (
                        section.find("span", attrs={"itemprop": "postalCode"}).get_text(  # type: ignore
                            strip=True
                        )
                        if section.find("span", attrs={"itemprop": "postalCode"})  # type: ignore
                        else ""
                    )
                    company["country"] = (
                        section.find(  # type: ignore
                            "span", attrs={"itemprop": "addressCountry"}  # type: ignore
                        ).get_text(
                            strip=True
                        )  # type: ignore
                        if section.find("span", attrs={"itemprop": "addressCountry"})  # type: ignore
                        else ""
                    )
                    company["phone"] = (
                        section.find("span", class_="phone-header")["data-phone-number"]  # type: ignore
                        if section.find("span", class_="phone-header")  # type: ignore
                        else ""
                    )

                    websites = section.find_all(  # type: ignore
                        "div", class_="company-header-www d-flex"
                    )
                    for web_div in websites:
                        website_link = (
                            web_div.find("a")["href"] if web_div.find("a") else ""  # type: ignore
                        )
                        if website_link:
                            company["website"] = website_link

                detailed_companies.append(company)
                time.sleep(delay)

            except Exception as e:
                print(f"Error processing {company['name']}: {str(e)}")
                detailed_companies.append(company)
                continue

        return detailed_companies

    def scrape_company_content(self, companies):
        for i, company in enumerate(companies):
            if "website" not in company or not company["website"]:
                company["description"] = ""
                continue

            print(
                f"Extracting content from website for {company['name']} ({i+1}/{len(companies)})"
            )

            try:
                response = requests.post(
                    self.neuscraper_endpoint, json={"url": company["website"]}
                )

                if response.status_code == 200:
                    company["description"] = response.json()["Text"]
                    print(
                        f"Successfully extracted content ({len(company['description'])} characters)"
                    )
                else:
                    print(
                        f"Failed to extract content. Status code: {response.status_code}"
                    )
                    company["description"] = ""

                time.sleep(5)

            except Exception as e:
                print(f"Error extracting content for {company['name']}: {str(e)}")
                company["description"] = ""

        return companies

    def save_company_data(self, companies, filename=None):
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"companies_{timestamp}"

        df = pd.DataFrame(companies)
        csv_path = os.path.join(self.data_dir, f"{filename}.csv")
        df.to_csv(csv_path, index=False)

        json_path = os.path.join(self.data_dir, f"{filename}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(companies, f, ensure_ascii=False, indent=4)

        print(f"Saved {len(companies)} companies to {csv_path} and {json_path}")
        return csv_path, json_path

    def load_company_data(self, filename):
        json_path = os.path.join(self.data_dir, f"{filename}.json")
        if not os.path.exists(json_path):
            print(f"File not found: {json_path}")
            return []

        with open(json_path, "r", encoding="utf-8") as f:
            companies = json.load(f)

        print(f"Loaded {len(companies)} companies from {json_path}")
        return companies

    def list_saved_datasets(self):
        json_files = [
            f.replace(".json", "")
            for f in os.listdir(self.data_dir)
            if f.endswith(".json")
        ]
        return json_files

    def run_full_pipeline(self, search_query, page_limit=1):
        print(f"Starting pipeline for query: '{search_query}'")

        companies = self.scrape_yellow_pages(search_query, page_limit)
        print(f"Found {len(companies)} companies from Yellow Pages")

        detailed_companies = self.scrape_company_details(companies)
        print(f"Collected details for {len(detailed_companies)} companies")

        enriched_companies = self.scrape_company_content(detailed_companies)
        print(f"Enriched {len(enriched_companies)} companies with website content")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        search_query_slug = search_query.lower().replace(" ", "_")
        filename = f"{search_query_slug}_{timestamp}"
        csv_path, json_path = self.save_company_data(enriched_companies, filename)

        print(f"Pipeline completed! Data saved to {json_path}")
        return filename


def main():
    st.set_page_config(page_title="Company Intelligence Pipeline", layout="wide")

    pipeline = CompanyIntelligencePipeline()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "current_dataset" not in st.session_state:
        st.session_state.current_dataset = None

    if "current_company" not in st.session_state:
        st.session_state.current_company = None

    if "chat" not in st.session_state:
        st.session_state.chat = None

    st.title("Company Intelligence Platform")

    tab1, tab2, tab3 = st.tabs(
        ["Data Collection", "Company Explorer", "Chat Assistant"]
    )

    with tab1:
        st.header("Collect Company Data")

        search_query = st.text_input(
            "Search Query (e.g., 'IT Software', 'Banking Jakarta')",
            placeholder="What kind of company are you interested in?",
        )

        if st.button("🔍 Start Data Collection"):
            with st.spinner("Collecting company data... This may take several minutes"):
                filename = pipeline.run_full_pipeline(search_query)
                st.session_state.current_dataset = filename
                st.success(
                    f"✅ Data collection completed! Collected data for search: '{search_query}'"
                )

        st.subheader("Available Datasets")
        datasets = pipeline.list_saved_datasets()
        if datasets:
            selected_dataset = st.selectbox("Select a dataset to load", datasets)
            if st.button("Load Dataset"):
                st.session_state.current_dataset = selected_dataset
                st.success(f"Loaded dataset: {selected_dataset}")
        else:
            st.info("No saved datasets found. Run data collection to create one.")

    with tab2:
        st.header("Explore Company Data")

        if not st.session_state.current_dataset:
            st.warning(
                "Please select or collect a dataset first in the Data Collection tab."
            )
        else:
            companies = pipeline.load_company_data(st.session_state.current_dataset)

            if not companies:
                st.warning("Selected dataset is empty or could not be loaded.")
            else:
                st.subheader(
                    f"Companies in dataset: {st.session_state.current_dataset}"
                )

                company_names = [company["name"] for company in companies]
                selected_company_name = st.selectbox(
                    "Select a company to view details", company_names
                )

                selected_company = next(
                    (
                        company
                        for company in companies
                        if company["name"] == selected_company_name
                    ),
                    None,
                )

                if selected_company:
                    st.session_state.current_company = selected_company

                    with st.expander("Company Details", expanded=True):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(f"### {selected_company['name']}")
                            st.markdown(
                                f"**Address:** {selected_company.get('street_address', '')} {selected_company.get('postal_code', '')}"
                            )
                            st.markdown(
                                f"**Phone:** {selected_company.get('phone', 'N/A')}"
                            )

                        with col2:
                            has_website = (
                                "website" in selected_company
                                and selected_company["website"]
                            )
                            if has_website:
                                st.markdown(
                                    f"**Website:** [{selected_company['website']}]({selected_company['website']})"
                                )
                            else:
                                st.markdown("**Website:** N/A")
                            st.markdown(
                                f"**Country:** {selected_company.get('country', 'N/A')}"
                            )

                    st.subheader("Website Content")

                    if not has_website:
                        st.warning("⚠️ This company doesn't have a website listed.")
                    else:
                        has_description = (
                            "description" in selected_company
                            and selected_company["description"]
                        )

                        if st.button(
                            "🔍 Find more information in the company website",
                            key="scrape_btn",
                        ):
                            with st.spinner(
                                f"Finding more information from {selected_company['website']}..."
                            ):
                                try:
                                    response = requests.post(
                                        pipeline.neuscraper_endpoint,
                                        json={"url": selected_company["website"]},
                                        timeout=60,
                                    )

                                    if response.status_code == 200:
                                        result = response.json()
                                        if "Text" in result and result["Text"].strip():
                                            selected_company["description"] = result[
                                                "Text"
                                            ]
                                            st.session_state.current_company[
                                                "description"
                                            ] = result["Text"]

                                            for i, company in enumerate(companies):
                                                if (
                                                    company["name"]
                                                    == selected_company["name"]
                                                ):
                                                    companies[i]["description"] = (
                                                        result["Text"]
                                                    )
                                                    break

                                            pipeline.save_company_data(
                                                companies,
                                                st.session_state.current_dataset,
                                            )
                                            st.success(
                                                "✅ Successfully gather more information from the website!"
                                            )
                                        else:
                                            st.error(
                                                "⛔ No relevant information could be extracted from the website. The website might have special formatting or anti-scraping measures."
                                            )
                                    else:
                                        st.error(
                                            f"⛔ Failed to find {selected_company["website"]}"
                                        )
                                except requests.exceptions.Timeout:
                                    st.error(
                                        "⏱️ Request to NeuScraper timed out. The website might be slow or unresponsive."
                                    )
                                except requests.exceptions.ConnectionError:
                                    st.error(
                                        "🔌 Connection to NeuScraper failed. Please check if the NeuScraper service is running."
                                    )
                                except Exception as e:
                                    st.error(f"❌ An error occurred: {str(e)}")

                    if (
                        "description" in selected_company
                        and selected_company["description"]
                    ):
                        with st.expander(
                            "Company Description (from website)", expanded=True
                        ):
                            description_text = selected_company["description"]
                            st.markdown(
                                description_text[:1000] + "..."
                                if len(description_text) > 1000
                                else description_text
                            )

                            if st.button("💬 Chat about this company"):
                                st.session_state.chat = create_chat_for_company(
                                    pipeline.gemini_client, selected_company
                                )
                                st.session_state.chat_history = []
                                st.success(
                                    "Chat initialized! Go to Chat Assistant tab to ask questions."
                                )
                    else:
                        if has_website:
                            st.info(
                                "No website content has been retrieved yet. Use the 'Find more information in the website' button above to obtain information."
                            )
                        else:
                            st.info("No website available for this company.")

    with tab3:
        st.header("Chat with AI assistant about Companies")

        if not st.session_state.current_company:
            st.warning("Please select a company in the Company Explorer tab first.")
        else:
            chat_container = st.container()

            if not st.session_state.chat:
                st.session_state.chat = create_chat_for_company(
                    pipeline.gemini_client, st.session_state.current_company
                )
                st.session_state.chat_history = []

            with chat_container:
                for i, msg in enumerate(st.session_state.chat_history):
                    if msg["role"] == "user":
                        message(msg["content"], is_user=True, key=f"{i}_user")
                    else:
                        message(msg["content"], is_user=False, key=f"{i}_ai")

            user_question = st.chat_input("Ask about this company...")

            if user_question:
                st.session_state.chat_history.append(
                    {"role": "user", "content": user_question}
                )
                message(user_question, is_user=True, key="latest_user")

                try:
                    with st.spinner("AI assistant is thinking..."):
                        response = st.session_state.chat.send_message(user_question)
                        bot_reply = response.text

                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": bot_reply}
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error getting response: {str(e)}")


def create_chat_for_company(client, company):
    company_info = f"""
    Company Name: {company.get('name', 'N/A')}
    Address: {company.get('street_address', '')} {company.get('postal_code', '')}
    Country: {company.get('country', 'N/A')}
    Phone: {company.get('phone', 'N/A')}
    Website: {company.get('website', 'N/A')}
    
    Company Description:
    {company.get('description', 'No description available')}
    """

    system_prompt = f"""You are a helpful business analyst assistant. Use the following information about the company to answer questions:
    
    {company_info}
    
    When answering questions, only use information from this content. If the information is not in the content, say so clearly.
    Be concise and professional in your answers.
    """

    try:
        chat = client.chats.create(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt, seed=42
            ),
        )
        return chat
    except Exception as e:
        print(f"Error creating chat: {str(e)}")
        return None


if __name__ == "__main__":
    main()
