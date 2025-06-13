from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

def accept_cookies(driver, logger):
    """Accept cookies by clicking the appropriate button."""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Wait for the cookie banner to be visible
            cookie_banner = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "onetrust-banner-sdk"))
            )
            
            # Wait for the accept button to be clickable
            accept_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            
            # Scroll the button into view if needed
            driver.execute_script("arguments[0].scrollIntoView(true);", accept_button)
            time.sleep(1)  # Small delay to ensure the button is fully visible
            
            # Try to click the button
            accept_button.click()
            
            # Wait for the banner to disappear
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.ID, "onetrust-banner-sdk"))
            )
            
            logger.info("Successfully accepted cookies.")
            return True
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to accept cookies: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("Failed to accept cookies after all attempts")
                return False
    
    return False

def change_date(driver, date, logger):
    """Change the date using the date picker."""
    try:
        date_str = date.strftime('%d/%m/%Y')
        
        date_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "datepicker-intraday"))
        )
        
        date_input.clear()
        date_input.send_keys(date_str)
        
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "arrow-submit"))
        )
        submit_button.click()
        
        time.sleep(5)
        
        return True
    except Exception as e:
        logger.error(f"Error changing date to {date_str}: {str(e)}")
        return False

def extract_demand_data(driver, date, logger):
    """Extract demand data from the table for a specific date."""
    try:
        table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "table-row"))
        )
        
        data = {'date': date.strftime('%Y-%m-%d')}
        
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) == 2:
                label = cells[0].text.strip()
                value = cells[1].text.strip().replace('GWh', '').strip()
                value = float(value.replace(',', ''))
                
                if "Final Demand" in label:
                    data['final_demand'] = value
                elif "Natural gas for power generation" in label:
                    data['power_generation'] = value
                elif "LNG trucks" in label:
                    data['lng_trucks'] = value
                elif "Total demand" in label:
                    data['total_demand'] = value
        
        return data
        
    except Exception as e:
        logger.error(f"Error extracting data for date {date}: {str(e)}")
        return None
