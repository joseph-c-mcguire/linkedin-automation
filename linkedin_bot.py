from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import json
import os
from time import sleep
from dotenv import load_dotenv
from logger_config import setup_logger
from gpt_handler import GPTHandler
from resume_parser import ResumeParser
import time
import random
from datetime import datetime, timedelta


class LinkedInBot:
    def __init__(self):
        self.logger = setup_logger()
        self.logger.info("Initializing LinkedIn Bot")
        load_dotenv()
        with open("config.json") as f:
            self.config = json.load(f)
        resume_parser = ResumeParser(self.config["resume_path"])
        self.gpt_handler = GPTHandler(
            api_key=self.config["openai_api_key"],
            resume_content=resume_parser.get_resume_content(),
        )
        self.daily_application_limit = 15
        self.applications_today = 0
        self.last_action_time = datetime.now()
        self.session_start_time = datetime.now()
        self.setup_driver()
        self.login()

    def random_delay(self, min_seconds=2, max_seconds=5):
        """Add random delay between actions"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def setup_driver(self):
        self.logger.info("Setting up Edge WebDriver")
        options = webdriver.EdgeOptions()
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")

        # Add random user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/92.0.902.78 Safari/537.36",
        ]
        options.add_argument(f"user-agent={random.choice(user_agents)}")

        service = EdgeService(EdgeChromiumDriverManager().install())
        self.driver = webdriver.Edge(service=service, options=options)
        self.logger.debug("WebDriver setup complete")

    def should_continue(self):
        """Check if we should continue applying"""
        if self.applications_today >= self.daily_application_limit:
            self.logger.info("Daily application limit reached")
            return False

        # Add cooldown between actions
        time_since_last_action = datetime.now() - self.last_action_time
        if time_since_last_action.seconds < random.uniform(30, 60):
            self.random_delay(5, 10)

        # Add session length limit (4 hours)
        if datetime.now() - self.session_start_time > timedelta(hours=4):
            self.logger.info("Session time limit reached")
            return False

        return True

    def natural_scroll(self):
        """Perform natural scrolling behavior"""
        scroll_pause_time = random.uniform(1, 3)
        total_height = int(
            self.driver.execute_script("return document.body.scrollHeight")
        )
        scroll_position = 0

        while scroll_position < total_height:
            scroll_step = random.randint(100, 400)
            scroll_position += scroll_step
            self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
            self.random_delay(0.5, 1.5)

    def login(self):
        self.logger.info("Attempting to log in to LinkedIn")
        self.driver.get("https://www.linkedin.com/login")

        # Wait for and fill in email
        email_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        email_field.send_keys(self.config["email"])
        self.logger.debug("Email entered")

        # Fill in password
        password_field = self.driver.find_element(By.ID, "password")
        password_field.send_keys(self.config["password"])
        self.logger.debug("Password entered")

        # Click login button
        login_button = self.driver.find_element(
            By.CSS_SELECTOR, "button[type='submit']"
        )
        login_button.click()
        self.logger.info("Login form submitted")

        sleep(5)
        self.logger.info("Login completed")

    def wait_for_jobs_to_load(self, max_retries=3):
        """Wait for job listings to become visible with retries"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                self.logger.info(
                    f"Waiting for job listings to load (attempt {retry_count + 1})..."
                )

                # Wait for jobs container with multiple possible selectors
                for selector in [
                    "div.jobs-search-results-list",
                    "ul.jobs-search-results__list",
                    "div.scaffold-layout__list-container",
                    "div.jobs-search__results-list",
                ]:
                    try:
                        element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if element.is_displayed():
                            self.logger.info(
                                f"Found visible jobs container with selector: {selector}"
                            )
                            return True
                    except:
                        continue

                # If no selectors worked, try scrolling and waiting
                self.logger.info("Scrolling page to trigger job loading...")
                self.driver.execute_script("window.scrollTo(0, 200)")
                self.random_delay(2, 3)
                retry_count += 1

            except Exception as e:
                self.logger.error(f"Error waiting for jobs to load: {str(e)}")
                retry_count += 1

            if retry_count < max_retries:
                self.logger.warning("Job listings not found, refreshing page...")
                self.driver.refresh()
                self.random_delay(5, 7)

        return False

    def search_jobs(self):
        self.logger.info(
            f"Searching jobs for: {self.config['job_title']} in {self.config['location']}"
        )

        # Construct search URL with better filtering
        search_url = (
            "https://www.linkedin.com/jobs/search/?"
            + f"keywords={self.config['job_title']}&"
            + f"location={self.config['location']}&"
            + "f_AL=true&"  # Easy Apply filter
            + "f_WT=2&"  # Full-time
            + "sortBy=DD&"  # Most recent
            + "position=1&"
            + "pageNum=0&"
            + "f_TPR=r86400"  # Last 24 hours
        )

        self.driver.get(search_url)
        self.random_delay(5, 7)  # Increased initial wait time

        if not self.wait_for_jobs_to_load():
            self.logger.error("Failed to load job listings after multiple attempts")
            return []

        # Try to find jobs with various selectors
        jobs = []
        job_selectors = [
            "div.job-card-container",
            "li.jobs-search-results__list-item",
            "div.job-card-list__entity-lockup",
            "div[data-job-id]",
        ]

        for selector in job_selectors:
            try:
                jobs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if jobs:
                    self.logger.info(
                        f"Found {len(jobs)} jobs using selector: {selector}"
                    )
                    # Verify jobs are actually loaded
                    try:
                        for i, job in enumerate(jobs[:3], 1):  # Check first 3 jobs
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView(true);", job
                            )
                            self.random_delay(1, 2)
                            title = job.find_element(
                                By.CSS_SELECTOR, "a.job-card-list__title"
                            ).text
                            self.logger.info(f"Verified job {i}: {title}")
                        return jobs
                    except Exception as e:
                        self.logger.error(f"Error verifying jobs: {str(e)}")
                        continue
            except:
                continue

        self.logger.error("No valid jobs found with any selector")
        return []

    def is_easy_apply(self):
        """Check if current job has Easy Apply button"""
        try:
            # Updated selectors to match LinkedIn's button structure
            button_selectors = [
                "button.jobs-apply-button.artdeco-button--3",
                "button.jobs-apply-button.artdeco-button--primary",
                "button[data-live-test-job-apply-button]",
                "button.artdeco-button--primary[aria-label*='Easy Apply to']",
                ".jobs-apply-button",  # Fallback
            ]

            for selector in button_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed():
                            # Check either button text or aria-label
                            button_text = button.text.lower()
                            aria_label = button.get_attribute("aria-label", "").lower()
                            if ("easy apply" in button_text) or (
                                "easy apply to" in aria_label
                            ):
                                self.logger.info(
                                    f"Found Easy Apply button: {aria_label}"
                                )
                                return True
                except:
                    continue
            return False
        except Exception as e:
            self.logger.error(f"Error checking Easy Apply button: {str(e)}")
            return False

    def apply_to_jobs(self, jobs):
        self.logger.info("Starting job application process")
        applied_count = 0

        for index, job_card in enumerate(jobs, 1):
            if not self.should_continue():
                break

            try:
                self.logger.info(f"Checking job {index}")

                # Try multiple selectors for job title
                title_selectors = [
                    "a.job-card-list__title",
                    "h3.job-card-list__title",
                    "a.disabled.ember-view.job-card-container__link.job-card-list__title",
                    ".job-card-container__link",
                    ".jobs-search-results__list-item-title",
                ]

                job_title_element = None
                for selector in title_selectors:
                    try:
                        job_title_element = job_card.find_element(
                            By.CSS_SELECTOR, selector
                        )
                        if job_title_element.is_displayed():
                            break
                    except:
                        continue

                if not job_title_element:
                    self.logger.error("Could not find job title element")
                    continue

                # Scroll job into view and click
                self.logger.info(f"Found job: {job_title_element.text}")
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    job_title_element,
                )
                self.random_delay(1, 2)

                try:
                    job_title_element.click()
                except:
                    self.driver.execute_script(
                        "arguments[0].click();", job_title_element
                    )

                self.random_delay(2, 3)

                # Check if it's Easy Apply
                if not self.is_easy_apply():
                    self.logger.info("Not an Easy Apply job, skipping...")
                    continue

                # Click Easy Apply button with updated selectors
                easy_apply_clicked = False
                button_selectors = [
                    "button.jobs-apply-button.artdeco-button--3",
                    "button.jobs-apply-button.artdeco-button--primary",
                    "button[data-live-test-job-apply-button]",
                    "button.artdeco-button--primary[aria-label*='Easy Apply to']",
                ]

                for selector in button_selectors:
                    try:
                        # Find all matching buttons
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for button in buttons:
                            if button.is_displayed():
                                aria_label = button.get_attribute(
                                    "aria-label", ""
                                ).lower()
                                button_text = button.text.lower()

                                if ("easy apply" in button_text) or (
                                    "easy apply to" in aria_label
                                ):
                                    self.logger.info(
                                        f"Clicking Easy Apply button: {aria_label}"
                                    )
                                    # Scroll into view
                                    self.driver.execute_script(
                                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                        button,
                                    )
                                    self.random_delay(1, 2)

                                    try:
                                        button.click()
                                    except:
                                        self.driver.execute_script(
                                            "arguments[0].click();", button
                                        )

                                    easy_apply_clicked = True
                                    self.random_delay(2, 3)
                                    break
                        if easy_apply_clicked:
                            break
                    except Exception as e:
                        self.logger.debug(
                            f"Failed to click button with selector {selector}: {str(e)}"
                        )
                        continue

                if not easy_apply_clicked:
                    self.logger.error("Could not click Easy Apply button")
                    continue

                self.random_delay(2, 3)

                # Handle the application
                try:
                    self.handle_application_form()
                    applied_count += 1
                    self.applications_today += 1
                    self.last_action_time = datetime.now()

                    # Add random delay between applications
                    self.random_delay(45, 90)
                except Exception as e:
                    self.logger.error(f"Error in application process: {str(e)}")
                    # Try to close the application modal if it's still open
                    try:
                        close_button = self.driver.find_element(
                            By.CSS_SELECTOR, "button[aria-label='Dismiss']"
                        )
                        close_button.click()
                    except:
                        pass
                    continue

            except Exception as e:
                self.logger.error(f"Error processing job {index}: {str(e)}")
                continue

            self.random_delay(3, 5)

        self.logger.info(
            f"Application process completed. Applied to {applied_count} jobs."
        )

    def handle_application_form(self):
        """Handle the Easy Apply form"""
        while True:  # Loop through multi-step applications
            try:
                # Wait for form to load
                time.sleep(2)

                # Check for next button or submit button
                next_button = None
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                "button[aria-label='Continue to next step']",
                            )
                        )
                    )
                except:
                    # Try to find submit button if next button isn't present
                    try:
                        next_button = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located(
                                (
                                    By.CSS_SELECTOR,
                                    "button[aria-label='Submit application']",
                                )
                            )
                        )
                    except:
                        break  # No more steps

                # Handle form fields on current step
                self.fill_form_fields()

                # Click next/submit button
                if next_button and next_button.is_enabled():
                    next_button.click()
                    time.sleep(2)
                else:
                    break

            except Exception as e:
                self.logger.error(f"Error in application form step: {str(e)}")
                raise

    def fill_form_fields(self):
        """Fill in all fields in the current form step"""
        # Find all input fields
        input_fields = self.driver.find_elements(By.TAG_NAME, "input")
        textareas = self.driver.find_elements(By.TAG_NAME, "textarea")

        # Handle each input field
        for field in input_fields + textareas:
            try:
                # Skip hidden or readonly fields
                if not field.is_displayed() or field.get_attribute("readonly"):
                    continue

                # Get field label or placeholder
                label = ""
                try:
                    label = (
                        field.get_attribute("aria-label")
                        or field.get_attribute("placeholder")
                        or ""
                    )
                except:
                    continue

                if label and not field.get_attribute("value"):
                    response = self.gpt_handler.generate_response(label)
                    for char in response:
                        field.send_keys(char)
                        self.random_delay(0.1, 0.3)
                    self.random_delay(0.5, 1.5)

            except Exception as e:
                self.logger.error(f"Error filling field: {str(e)}")
                continue

    def run(self):
        try:
            self.logger.info("Starting LinkedIn Bot")
            if not self.should_continue():
                self.logger.info("Daily limits reached, stopping bot")
                return

            jobs = self.search_jobs()
            self.apply_to_jobs(jobs)

        except Exception as e:
            self.logger.error(f"Critical error: {str(e)}")
        finally:
            self.logger.info(
                f"Session summary: Applied to {self.applications_today} jobs"
            )
            self.logger.info("Shutting down LinkedIn Bot")
            self.driver.quit()


if __name__ == "__main__":
    bot = LinkedInBot()
    bot.run()
