#!/usr/bin/env python3
# selenium_umniah_add_to_cart_checkout_Version4.py
# Improved: force navigation to checkout, detailed debug if it doesn't load

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import html

# CONFIG
PRODUCT_URL = "https://eshop.umniah.com/ar/%D8%A8%D8%B7%D8%A7%D9%82%D8%A9-%D9%87%D8%AF%D9%8A%D8%A9-%D8%A8%D8%A8%D8%AC%D9%8A-600-%D9%8A%D9%88-%D8%B3%D9%8A.html"
CHECKOUT_URL = "https://eshop.umniah.com/ar/checkout/index/"
TARGET_QTY = 2
HEADLESS = False
WAIT = 15

PHONE = "0790114370"
EMAIL = "custmernewallet@gmail.com"
FULL_NAME = "testtesttest"
PAYMENT_TEXT = "UWallet"

def make_driver(headless=HEADLESS):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    prefs = {"profile.managed_default_content_settings.images": 2}
    opts.add_experimental_option("prefs", prefs)
    try:
        opts.page_load_strategy = "eager"
    except Exception:
        opts.set_capability("pageLoadStrategy", "eager")
    service = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=service, options=opts)
    d.set_window_size(1200, 1000)
    return d

# minimal helpers (use same robust functions from v3 if you want)
def try_set_quantity(driver, qty):
    xps = ["//input[@type='number']", "//input[contains(@name,'qty') or contains(@name,'quantity') or contains(@id,'qty') or contains(@id,'quantity')]", "//input[@name='quantity']"]
    for xp in xps:
        try:
            el = WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.XPATH, xp)))
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].scrollIntoView();", el)
            try:
                el.clear()
            except Exception:
                driver.execute_script("arguments[0].value='';", el)
            el.send_keys(str(qty))
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
            time.sleep(0.6)
            print("✅ set qty via:", xp)
            return True
        except Exception:
            continue
    # fallback
    try:
        res = driver.execute_script("var e=document.querySelector('input[name=\"quantity\"], input[name=\"qty\"], input[type=\"number\"]'); if(e){ e.value=arguments[0]; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return true; } return false;", qty)
        if res:
            time.sleep(0.6)
            print("✅ set qty via JS fallback")
            return True
    except Exception:
        pass
    print("⚠️ couldn't set quantity automatically")
    return False

def click_add_to_cart(driver):
    # try common xpaths and text; return True if clicked
    candidates = [
        "//button[contains(normalize-space(.),'أضف إلى السلة') or contains(.,'Add to cart') or contains(.,'أضف')]",
        "//a[contains(.,'add to cart') or contains(.,'أضف')]",
        "//input[@type='submit' and (contains(@value,'أضف') or contains(@value,'Add'))]",
        "//*[contains(@class,'add-to-cart') or contains(@data-action,'add-to-cart')]"
    ]
    for xp in candidates:
        try:
            els = driver.find_elements(By.XPATH, xp)
        except Exception:
            els = []
        for el in els:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try:
                    el.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", el)
                time.sleep(1)
                print("✅ clicked add-to-cart via xp:", xp)
                return True
            except Exception:
                continue
    # broad fallback by text
    try:
        els = driver.find_elements(By.XPATH, "//*[contains(normalize-space(.),'أضف') or contains(normalize-space(.),'Add to cart') or contains(normalize-space(.),'اضف')]")
    except Exception:
        els = []
    for el in els:
        try:
            driver.execute_script("arguments[0].scrollIntoView();", el)
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", el)
            time.sleep(1)
            print("✅ clicked add-to-cart via broad search")
            return True
        except Exception:
            continue
    print("⚠️ add-to-cart button not clicked")
    return False

def force_go_to_checkout(driver):
    """
    Ensure we end up on the checkout page.
    Steps:
      - check current_url
      - try to click cart/checkout links/buttons if present
      - finally driver.get(CHECKOUT_URL)
      - wait for expected checkout fields
    Returns True if checkout appears ready, False otherwise (and writes debug HTML)
    """
    print("➡️ current_url before forcing:", driver.current_url)
    # If already on checkout URL or contains 'checkout'
    if 'checkout' in driver.current_url.lower():
        print("ℹ️ browser already on checkout URL.")
    else:
        # Try to click any link/button that points to checkout/cart
        try:
            links = driver.find_elements(By.XPATH, "//a[contains(@href,'checkout') or contains(@href,'cart') or contains(@class,'cart') or contains(@id,'cart')]")
        except Exception:
            links = []
        clicked = False
        for a in links:
            try:
                driver.execute_script("arguments[0].scrollIntoView();", a)
                try:
                    a.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", a)
                time.sleep(1.2)
                print("🔗 clicked cart/checkout link")
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            # try clicking any element that looks like a cart icon
            try:
                icons = driver.find_elements(By.CSS_SELECTOR, ".cart, .minicart, .header-cart, [data-role='minicart'] , .top-cart")
            except Exception:
                icons = []
            for ic in icons:
                try:
                    driver.execute_script("arguments[0].scrollIntoView();", ic)
                    try:
                        ic.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", ic)
                    time.sleep(1.2)
                    print("🛒 clicked cart icon")
                    clicked = True
                    break
                except Exception:
                    continue
        # finally, enforce nav
        if not clicked:
            print("⚠️ لم نجد رابط/أيقونة للعربة قابلة للنقر أو لم تعمل — سننتقل يدوياً لصفحة الدفع.")
        try:
            driver.get(CHECKOUT_URL)
            print("🔁 executed driver.get(CHECKOUT_URL)")
        except Exception as e:
            print("❌ driver.get(CHECKOUT_URL) failed:", e)

    # wait for checkout fields (longer wait)
    ready_xps = [
        "//input[@id='customer-email']",
        "//input[@type='tel']",
        "//input[contains(@name,'phone') or contains(@id,'phone')]"
    ]
    success = False
    for xp in ready_xps:
        try:
            WebDriverWait(driver, WAIT*1.5).until(EC.presence_of_element_located((By.XPATH, xp)))
            print("✅ checkout appears ready (found):", xp)
            success = True
            break
        except Exception:
            continue

    if not success:
        # dump debug HTML
        try:
            src = driver.page_source
            with open("checkout_debug.html", "w", encoding="utf-8") as f:
                f.write(src)
            print("⚠️ checkout not ready — saved page to checkout_debug.html for inspection.")
            # also print current URL and first 600 chars of body text
            try:
                print("current_url:", driver.current_url)
                body = driver.find_element(By.TAG_NAME, "body").text[:600]
                print("body snippet (600 chars):")
                print(body)
            except Exception:
                pass
        except Exception as e:
            print("❌ failed to save debug html:", e)
        return False
    return True

# minimal robust fill functions (can be copied from v3 if needed)
def simple_set_email(driver, email):
    xps = ["//input[@id='customer-email']", "//input[@type='email' and contains(@name,'email')]", "//input[contains(@placeholder,'email') or contains(@placeholder,'البريد')]"]
    for xp in xps:
        try:
            el = driver.find_element(By.XPATH, xp)
            driver.execute_script("arguments[0].scrollIntoView();", el)
            try:
                el.clear()
            except Exception:
                driver.execute_script("arguments[0].value='';", el)
            el.send_keys(email)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
            print("✅ set email via:", xp)
            return True
        except Exception:
            continue
    print("⚠️ could not set email automatically")
    return False

# reuse robust phone/name from previous file if you have them, else use simple attempts
def simple_set_phone(driver, phone):
    xps = ["//input[@type='tel']", "//input[contains(@name,'phone')]", "//input[contains(@id,'phone')]", "//input[@type='text' and contains(@placeholder,'رقم')]"]
    for xp in xps:
        try:
            el = driver.find_element(By.XPATH, xp)
            driver.execute_script("arguments[0].scrollIntoView();", el)
            try:
                el.clear()
            except Exception:
                driver.execute_script("arguments[0].value='';", el)
            el.send_keys(phone)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
            print("✅ set phone via:", xp)
            return True
        except Exception:
            continue
    print("⚠️ could not set phone automatically (simple).")
    return False

def main():
    driver = make_driver()
    try:
        print("🔗 open product page...")
        driver.get(PRODUCT_URL)
        try:
            WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except Exception:
            pass

        ok = try_set_quantity(driver, TARGET_QTY)
        print("set qty ->", ok)
        time.sleep(0.6)
        added = click_add_to_cart(driver)
        print("add to cart clicked ->", added)

        # print URL and make sure checkout loads
        print("🔍 current_url after add:", driver.current_url)
        ok_checkout = force_go_to_checkout(driver)
        if not ok_checkout:
            print("❌ checkout did not load correctly — inspect checkout_debug.html and paste here or send screenshot.")
            return

        # if checkout ready, fill basic fields (email/phone/name) then continue
        simple_set_email(driver, EMAIL)
        simple_set_phone(driver, PHONE)
        # (optionally set name; reuse robust functions if available)
        # pause so you can see
        print("⏳ filled basic fields, waiting 2s for manual check...")
        time.sleep(2)

        # you can continue with your robust fill/submit logic here (ensure_terms_checked, etc.)
        # for demo, we stop after verifying checkout loaded
        print("✅ checkout loaded and basic fields set. You can continue the rest of the flow now.")

    finally:
        print("⏹️ done (not closing browser immediately to let you inspect). Waiting 6 sec then quitting.")
        time.sleep(6)
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == '__main__':
    main()
