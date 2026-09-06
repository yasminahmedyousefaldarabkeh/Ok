#!/usr/bin/env python3
# selenium_umniah_debug.py
# Requirements:
#   pip install selenium webdriver-manager
# Usage:
#   python selenium_umniah_debug.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

PRODUCT_URL = "https://eshop.umniah.com/ar/%D8%A8%D8%B7%D8%A7%D9%82%D8%A9-%D9%87%D8%AF%D9%8A%D8%A9-%D8%A8%D8%A8%D8%AC%D9%8A-600-%D9%8A%D9%88-%D8%B3%D9%8A.html"
CHECKOUT_URL = "https://eshop.umniah.com/ar/checkout/index/"
PHONE = "0790114370"   # ضع رقمك هنا (يمكن أن يكون مع 0)
WAIT_TIMEOUT = 12

def make_driver(headless=False):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    prefs = {"profile.managed_default_content_settings.images": 2}
    opts.add_experimental_option("prefs", prefs)
    try:
        opts.page_load_strategy = "eager"
    except Exception:
        opts.set_capability("pageLoadStrategy", "eager")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_window_size(1200, 900)
    return driver

def debug_print_phone_inputs(driver):
    # هذا الجزء يجلب كل الحقول ويطبعهم في الطرفية (Terminal)
    js = """
    return Array.from(document.querySelectorAll(
      'input[type=\"tel\"], input[name*=\"phone\"], input[id*=\"phone\"], input[name*=\"telephone\"], input'
    )).map(i=>({
      outerHTML: i.outerHTML,
      id: i.id||null,
      name: i.name||null,
      value: i.value||null,
      placeholder: i.placeholder||null,
      className: i.className||null,
      hidden: (i.offsetParent===null)
    }));
    """
    try:
        inputs = driver.execute_script(js)
    except Exception as e:
        print("DEBUG: error executing JS to collect inputs:", e)
        return []
    print("DEBUG phone inputs (count={}):".format(len(inputs)))
    for idx, it in enumerate(inputs):
        print("--- INPUT", idx, "---")
        print("id:", it['id'], " name:", it['name'], " value:", it['value'], " placeholder:", it['placeholder'], " hidden:", it['hidden'])
        print(it['outerHTML'])
        print()
    # also return the raw list so caller can inspect
    return inputs

def set_tel_by_typing(driver, xpaths, value):
    if isinstance(xpaths, str):
        xpaths = [xpaths]
    for xp in xpaths:
        try:
            el = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.XPATH, xp)))
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            try:
                el.clear()
            except Exception:
                driver.execute_script("arguments[0].value = '';", el)
            cur = (el.get_attribute("value") or "").strip()
            val = value
            if cur.startswith("+962") and val.startswith("0"):
                val = val.lstrip("0")
            for ch in val:
                el.send_keys(ch)
                time.sleep(0.03)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true})); arguments[0].blur();", el)
            time.sleep(0.3)
            return True
        except Exception:
            continue
    # fallback: try intlTelInput.setNumber via JS
    try:
        num = value
        if num.startswith("0"):
            num = "+962" + num.lstrip("0")
        js = """
        var input = document.querySelector('input[type="tel"], input[name*="phone"], input[id*="phone"]');
        if(window.intlTelInput && input){
          try{
            var iti = window.intlTelInputGlobals.getInstance(input);
            if(iti && iti.setNumber){
              iti.setNumber(arguments[0]);
              input.dispatchEvent(new Event('input',{bubbles:true}));
              input.dispatchEvent(new Event('change',{bubbles:true}));
              return true;
            }
          }catch(e){ return 'err:'+e.toString(); }
        }
        return false;
        """
        res = driver.execute_script(js, num)
        if res:
            print("DEBUG: setNumber via intlTelInput result:", res)
            return True
    except Exception:
        pass
    return False

def main():
    driver = make_driver(headless=False)
    try:
        print("🔗 فتح صفحة المنتج...")
        driver.get(PRODUCT_URL)
        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            print("⚠️ تحميل صفحة المنتج بطئ، سنكمل للتشخيص...")

        # اذهب لصفحة الدفع (نحتاج نعرض الحقول هناك)
        print("🔗 الذهاب لصفحة الدفع...")
        driver.get(CHECKOUT_URL)
        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            print("⚠️ تحميل صفحة الدفع بطئ، سنكمل للتشخيص...")

        # طباعه الحقول لتشخيص
        inputs = debug_print_phone_inputs(driver)

        # نجرب نعبي الحقل باستخدام send_keys على بعض الـ XPaths الشائعة
        xpaths = [
            "//input[@type='tel']",
            "//input[contains(@name,'phone') or contains(@name,'telephone') or contains(@id,'telephone') or contains(@id,'phone')]",
            "//input[contains(@class,'phone') or contains(@class,'tel')]",
            "//input[@name='telephone' or @name='phone']"
        ]
        ok = set_tel_by_typing(driver, xpaths, PHONE)
        print("📱 محاولة تعبئة الهاتف عبر send_keys ->", "نجح" if ok else "فشل")

        # انتظر شوي وحط نهاية
        time.sleep(2)
        print("✅ انتهى الفحص. انسخ الناتج في الطرفية والصقه هنا.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
