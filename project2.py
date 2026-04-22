# CrewAI Workflow: Apartment Lease Analyzer (Enhanced)
# 4 agents collaborate to analyze lease terms, detect red flags,
# compare to market standards, and suggest negotiation points.
#
# Features demonstrated:
#   - Context chaining (context= between tasks)
#   - Structured Pydantic output (output_pydantic)
#   - Guardrail validation (guardrail= on red flag task)
#   - Human-in-the-loop (human_input=True on negotiation task)
#   - Task callback (progress tracking after each task)
#   - Output to file (output_file for final report)
#   - Dynamic chatbot-style input

from crewai import Agent, Task, Crew, Process
from crewai.tasks.task_output import TaskOutput
from crewai.tools import tool
from crewai_tools import ScrapeWebsiteTool, PDFSearchTool, FileReadTool
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
import smtplib
import os
from email.mime.text import MIMEText

load_dotenv()


# -------------------------
# Email Send Tool
# -------------------------
@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient via SMTP.
    Args:
        to: The recipient email address.
        subject: The email subject line.
        body: The full email body text.
    """
    sender = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["To"] = to
    msg["From"] = sender

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return f"Email successfully sent to {to}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


# -------------------------
# Structured Output Models
# -------------------------
class ClauseAssessment(BaseModel):
    """Assessment of a single lease clause."""
    clause: str = Field(description="The lease clause being assessed")
    severity: str = Field(description="RED, YELLOW, or GREEN")
    reason: str = Field(description="Why this severity was assigned")
    applicable_law: str = Field(description="Relevant law or standard, or 'N/A' if none")


class LeaseRedFlagReport(BaseModel):
    """Complete red flag report for a lease."""
    city: str = Field(description="City the lease is in")
    total_red_flags: int = Field(description="Number of RED severity clauses")
    total_warnings: int = Field(description="Number of YELLOW severity clauses")
    assessments: List[ClauseAssessment] = Field(description="Assessment for each clause")


# -------------------------
# Guardrail Function
# -------------------------
def validate_all_clauses_reviewed(output: TaskOutput) -> tuple[bool, str]:
    """Guardrail: ensures the red flag detector reviewed all key lease areas."""
    text = output.raw.lower()
    required_topics = ["rent", "deposit", "subletting", "termination", "pet", "entry"]

    missing = [topic for topic in required_topics if topic not in text]

    if missing:
        return (False,
                f"Incomplete review. You did not assess these clauses: {', '.join(missing)}. "
                f"You MUST review ALL lease clauses. Please try again.")

    return (True, output.raw)


# -------------------------
# Task Callback
# -------------------------
def on_task_complete(output: TaskOutput):
    """Called after each task completes. Tracks progress."""
    print("\n" + "=" * 55)
    print(f"  STAGE COMPLETE | Output: {len(output.raw)} characters")
    print("=" * 55 + "\n")


# -------------------------
# Agents
# -------------------------
web_scraper = Agent(
    role="Lease Data Extractor",
    goal="Extract lease-related information from URLs, uploaded documents, or raw text input.",
    backstory=(
        "You are an expert at extracting lease information from any source. "
        "You can scrape apartment listing web pages, read uploaded lease agreement "
        "documents (PDF, DOCX, TXT), or process raw text input. You extract all "
        "relevant details: rent, deposit, lease terms, restrictions, amenities, "
        "pet policies, and any other lease-related information."
    ),
    tools=[ScrapeWebsiteTool(), PDFSearchTool(), FileReadTool()],
    verbose=True
)

clause_extractor = Agent(
    role="Lease Clause Extractor",
    goal="Parse raw lease terms and organize them into clear, structured categories.",
    backstory=(
        "You are a legal assistant specializing in residential leases. "
        "You take messy lease terms and organize them into clean categories: "
        "rent, deposit, restrictions, penalties, landlord rights, and tenant obligations."
    ),
    verbose=True
)

red_flag_detector = Agent(
    role="Lease Red Flag Detector",
    goal="Identify unfair, unusual, or potentially illegal clauses in a lease agreement.",
    backstory=(
        "You are a tenant rights advocate with deep knowledge of landlord-tenant laws "
        "across US states. You have helped thousands of renters spot problematic lease "
        "clauses before they sign. You know common legal limits on deposits, notice periods, "
        "and tenant rights by state."
    ),
    verbose=True
)

comparison_agent = Agent(
    role="Market Comparison Analyst",
    goal="Compare lease terms against typical market standards for the given city.",
    backstory=(
        "You are a real estate market analyst who tracks rental trends across major US cities. "
        "You know typical rent ranges, standard deposit amounts, common lease restrictions, "
        "and what is considered normal vs. unusual for each market."
    ),
    verbose=True
)

negotiation_advisor = Agent(
    role="Lease Negotiation Advisor",
    goal="Provide specific, actionable negotiation points and draft a professional email to the landlord.",
    backstory=(
        "You are an experienced tenant negotiation coach. You help renters negotiate "
        "better lease terms by prioritizing what to push back on, what to accept, "
        "and how to communicate professionally with landlords to get results."
    ),
    verbose=True
)

email_sender = Agent(
    role="Email Dispatch Agent",
    goal="Send the finalized negotiation email to the landlord on behalf of the tenant.",
    backstory=(
        "You are a professional communications assistant. After the tenant has reviewed "
        "and approved the negotiation email, you format it properly with subject line, "
        "greeting, body, and sign-off, then use the send_email tool to deliver it."
    ),
    tools=[send_email],
    verbose=True
)

# -------------------------
# Tasks
# -------------------------
scrape_task = Task(
    description=(
        "Extract all lease-related information from the provided input.\n\n"
        "Input type: {inputType}\n"
        "Input: {leaseInput}\n\n"
        "Based on the input type:\n"
        "- If 'url': Use the ScrapeWebsiteTool to scrape the web page and extract lease info.\n"
        "- If 'file': Use PDFSearchTool (for PDFs) or FileReadTool (for DOCX/TXT) to read "
        "the uploaded document and extract lease info.\n"
        "- If 'text': The input already contains the lease terms — pass them through directly.\n\n"
        "Extract everything related to:\n"
        "- Rent amount and payment terms\n"
        "- Security deposit\n"
        "- Lease duration\n"
        "- Pet policy\n"
        "- Subletting rules\n"
        "- Move-in/move-out conditions\n"
        "- Landlord entry and notice policies\n"
        "- Any fees, penalties, or restrictions\n"
        "- Property details (address, city, bedrooms, amenities)\n\n"
        "Return ALL lease-related text found."
    ),
    expected_output=(
        "A comprehensive extraction of all lease terms, conditions, fees, "
        "restrictions, and property details from the provided input."
    ),
    agent=web_scraper
)

extract_task = Task(
    description=(
        "Parse the scraped apartment listing data and organize the lease terms "
        "into structured categories.\n\n"
        "City: {cityName}\n\n"
        "Organize into these categories:\n"
        "- Rent (monthly amount, due date, late fees)\n"
        "- Security Deposit (amount, conditions for return)\n"
        "- Restrictions (pets, subletting, guests, modifications)\n"
        "- Penalties (early termination, lease breaking fees)\n"
        "- Landlord Rights (entry notice, inspection rules)\n"
        "- Lease Duration and Renewal terms\n"
        "- Any other notable clauses"
    ),
    expected_output=(
        "A well-organized breakdown of all lease clauses sorted by category, "
        "with each term clearly stated."
    ),
    agent=clause_extractor,
    context=[scrape_task]
)

red_flag_task = Task(
    description=(
        "Review the structured lease clauses and identify any red flags.\n\n"
        "For the city of {cityName}, check each clause against known tenant protection laws.\n"
        "For each clause, provide:\n"
        "- The clause text\n"
        "- Severity: RED (likely illegal/very unfair), YELLOW (unusual/risky), GREEN (acceptable)\n"
        "- Why it is flagged (legal reason or fairness concern)\n"
        "- The applicable law or standard (or 'N/A')\n\n"
        "You MUST review ALL clauses including: rent, deposit, subletting, "
        "termination, pets, and landlord entry."
    ),
    expected_output=(
        "A structured assessment of each lease clause with severity, reasoning, "
        "and applicable laws."
    ),
    agent=red_flag_detector,
    context=[extract_task],
    output_pydantic=LeaseRedFlagReport,       # Structured Pydantic output
    guardrail=validate_all_clauses_reviewed,  # Guardrail validation
    guardrail_max_retries=2,
    human_input=True                          # HITL: review red flags before proceeding
)

compare_task = Task(
    description=(
        "Compare the lease terms against typical market standards for {cityName}.\n\n"
        "For each major term, state:\n"
        "- What this lease offers\n"
        "- What is typical in {cityName}\n"
        "- Verdict: ABOVE MARKET / AT MARKET / BELOW MARKET / NON-STANDARD\n\n"
        "Cover: rent amount, deposit, restrictions, penalties, and landlord access terms."
    ),
    expected_output=(
        "A term-by-term comparison table showing this lease vs. market standard, "
        "with a clear verdict for each."
    ),
    agent=comparison_agent,
    context=[extract_task, red_flag_task]
)

negotiate_task = Task(
    description=(
        "Based on all the findings, create a negotiation strategy for the tenant.\n\n"
        "Classify each lease item using ONLY these two color-coded categories:\n"
        "1. RED FLAG (illegal or not compliant with state/city law — must be changed)\n"
        "2. GREEN FLAG (acceptable — compliant and fair, no action needed)\n\n"
        "Do NOT use any middle/yellow category. Every item must be either RED FLAG or GREEN FLAG.\n\n"
        "For each RED FLAG item, suggest what to ask for specifically and cite the "
        "applicable state/city law or regulation that makes it non-compliant.\n\n"
        "Finally, draft a short, professional email the tenant can send to the landlord "
        "requesting the RED FLAG items be changed. Keep the tone polite but firm."
    ),
    expected_output=(
        "A two-bucket negotiation strategy labeled RED FLAG (illegal/non-compliant, with "
        "cited law and specific ask) and GREEN FLAG (acceptable), followed by a "
        "ready-to-send email draft to the landlord covering only the RED FLAG items."
    ),
    agent=negotiation_advisor,
    context=[extract_task, red_flag_task, compare_task],
    human_input=True,                           # Human reviews before finalizing
)

email_task = Task(
    description=(
        "Take the approved negotiation strategy and email draft from the previous task.\n\n"
        "Format the final email with:\n"
        "- Subject line\n"
        "- Professional greeting\n"
        "- The negotiation points and requests\n"
        "- Polite closing and sign-off\n\n"
        "Confirm the email is ready to send to the landlord. "
        "Include the recipient placeholder: {landlordEmail}\n"
        "Save the final email to file."
    ),
    expected_output=(
        "A fully formatted, ready-to-send email with subject line, body, "
        "and sign-off addressed to the landlord."
    ),
    agent=email_sender,
    context=[negotiate_task],
    human_input=True,                           # HITL: final confirmation before sending
    output_file="output/lease_email.md"         # Save final email to file
)

# -------------------------
# Crew
# -------------------------
lease_analyzer_crew = Crew(
    agents=[web_scraper, clause_extractor, red_flag_detector, comparison_agent, negotiation_advisor, email_sender],
    tasks=[scrape_task, extract_task, red_flag_task, compare_task, negotiate_task, email_task],
    process=Process.sequential,
    verbose=True,
    task_callback=on_task_complete               # Progress callback after each task
)

# -------------------------
# Dynamic Input (Chatbot-style)
# -------------------------
print("=" * 55)
print("  APARTMENT LEASE ANALYZER")
print("  Powered by CrewAI Multi-Agent System")
print("=" * 55)
print()

print("How would you like to provide the lease information?")
print("  1. Paste lease terms as text")
print("  2. Provide an apartment listing URL")
print("  3. Upload a lease document (PDF, DOCX, or TXT file path)")
print()
choice = input("Enter 1, 2, or 3: ").strip()

if choice == "2":
    input_type = "url"
    lease_input = input("Paste the apartment listing URL:\n> ").strip()
    if not lease_input:
        lease_input = "https://www.apartments.com"
        print(f"\n  No URL provided. Using example: {lease_input}\n")
elif choice == "3":
    input_type = "file"
    lease_input = input("Enter the file path to the lease document:\n> ").strip()
    if not lease_input or not os.path.exists(lease_input):
        print("  Invalid file path. Please provide a valid path to a PDF, DOCX, or TXT file.")
        exit(1)
else:
    input_type = "text"
    lease_input = input("Paste your lease terms:\n> ").strip()
    if not lease_input:
        lease_input = (
            "$1800/month rent, 2-month security deposit, no subletting allowed, "
            "$500 early termination fee, no pets, landlord can enter with 12-hour notice, "
            "rent increases up to 10% annually, tenant responsible for all repairs under $200, "
            "lease auto-renews for 12 months if not cancelled 90 days before expiry"
        )
        print(f"\n  Using example lease terms.\n")

city_name = input("City name: ").strip()
landlord_email = input("Landlord email address: ").strip()

if not city_name:
    city_name = "San Francisco"
    print(f"  Using default city: {city_name}\n")

if not landlord_email:
    landlord_email = "landlord@example.com"
    print(f"  Using placeholder email: {landlord_email}\n")

inputs = {
    "inputType": input_type,
    "leaseInput": lease_input,
    "cityName": city_name,
    "landlordEmail": landlord_email
}

print(f"\n  Input type: {input_type}")
print(f"  Input: {lease_input[:80]}...")
print(f"  City: {city_name}")
print(f"\n  NOTE: You will be asked to review the analysis before the final report.\n")

# -------------------------
# Run
# -------------------------
result = lease_analyzer_crew.kickoff(inputs=inputs)

print("\n" + "=" * 55)
print("  LEASE ANALYSIS COMPLETE")
print("  Report saved to: output/lease_report.md")
print("  Email saved to: output/lease_email.md")
print("=" * 55 + "\n")
print(result)
