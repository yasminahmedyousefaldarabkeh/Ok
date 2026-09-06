#!/usr/bin/env python3
# success.devtools
# Selenium flow: product -> add to cart -> checkout -> fill -> place order -> wait success (never auto-exit)
# Usage:
#   pip install selenium webdriver-manager
#   python success.devtools

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

# ====== CONFIG ======
PRODUCT_URL = "https://eshop.umniah.com/ar/%D8%A8%D8%B7%D8%A7%D9%82%D8%A9-%D9%87%D8%AF%D9%8A%D8%A9-%D8%A8%D8%A8%D8%AC%D9%8A-600-%D9%8A%D9%88-%D8%B3%D9%8A.html"
CHECKOUT_URL = "https://eshop.umniah.com/ar/checkout/index/"
SUCCESS_URL_PART = "/checkout/onepage/success"
TARGET_QTY = 2
HEADLESS = False
WAIT = 15

# بيانات العميل — عدّل حسب الحاجة
PHONE = "0790114370"
EMAIL = "custmernewallet@gmail.com"
FULL_NAME = "testtesttest"
PAYMENT_TEXT = "UWallet"  # نص طريقة الدفع للبحث عنها

# ====== driver setup ======
def make_driver(headless=HEADLESS):
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
    driver.set_window_size(1200, 1000)
    return driver

# ====== helpers (مختصرة ومجربة) ======
def try_set_quantity(driver, qty):
    xps = ["//input[@type='number']", "//input[contains(@name,'qty') or contains(@name,'quantity') or contains(@id,'qty')]", "//input[@name='quantity']"]
    for xp in xps:
        try:
            el = WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.XPATH, xp)))
            try: el.click()
            except Exception: driver.execute_script("arguments[0].scrollIntoView();", el)
            try: el.clear()
            except Exception: driver.execute_script("arguments[0].value='';", el)
            el.send_keys(str(qty))
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
            time.sleep(0.6)
            print("✅ ضبطت الكمية عبر xpath:", xp)
            return True
        except Exception:
            continue
    try:
        res = driver.execute_script("var e=document.querySelector('input[name=\"quantity\"], input[name=\"qty\"], input[type=\"number\"]'); if(e){ e.value=arguments[0]; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return true; } return false;", qty)
        if res:
            time.sleep(0.6)
            print("✅ ضبطت الكمية عبر fallback JS")
            return True
    except Exception:
        pass
    print("⚠️ تعذّر ضبط الكمية تلقائياً")
    return False

def click_add_to_cart(driver):
    candidates = ["//button[contains(normalize-space(.),'أضف إلى السلة') or contains(.,'Add to cart') or contains(.,'أضف')]",
                  "//a[contains(.,'add to cart') or contains(.,'أضف')]",
                  "//input[@type='submit' and (contains(@value,'أضف') or contains(@value,'Add'))]",
                  "//*[contains(@class,'add-to-cart') or contains(@data-action,'add-to-cart')]"]
    for xp in candidates:
        try:
            els = driver.find_elements(By.XPATH, xp)
        except Exception:
            els = []
        for el in els:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try: el.click()
                except Exception: driver.execute_script("arguments[0].click();", el)
                time.sleep(1)
                print("✅ clicked add-to-cart via xp:", xp)
                return True
            except Exception:
                continue
    print("⚠️ add-to-cart button not clicked")
    return False

def go_to_checkout_from_cart(driver):
    proceed_xps = [
        "//a[contains(normalize-space(.),'الذهاب للدفع') or contains(normalize-space(.),'الدفع') or contains(normalize-space(.),'تابع') or contains(normalize-space(.),'Proceed to checkout') or contains(normalize-space(.),'Checkout')]",
        "//button[contains(normalize-space(.),'المتابعة للدفع') or contains(normalize-space(.),'الدفع') or contains(.,'Checkout') or contains(.,'متابعة')]",
        "//a[contains(@href,'checkout') or contains(@href,'/checkout/')]",
        "//button[contains(@onclick,'checkout') or contains(@data-action,'checkout')]"
    ]
    for xp in proceed_xps:
        try:
            els = driver.find_elements(By.XPATH, xp)
        except Exception:
            els = []
        for el in els:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try: el.click()
                except Exception: driver.execute_script("arguments[0].click();", el)
                time.sleep(1.2)
                # wait for checkout indicators
                try:
                    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, "//input[@id='customer-email' or @type='tel']")))
                    return True
                except Exception:
                    pass
            except Exception:
                continue
    return False

def force_go_to_checkout(driver):
    cur = driver.current_url
    print("➡️ current_url after add:", cur)
    # if on cart page, try proceed
    if '/checkout/cart' in cur or '/cart' in cur or 'cart' in cur.lower():
        ok = go_to_checkout_from_cart(driver)
        if ok:
            print("✅ moved to checkout after clicking proceed on cart.")
            return True
    # try checkout links
    try:
        links = driver.find_elements(By.XPATH, "//a[contains(@href,'/checkout') or contains(@href,'checkout/index')]")
    except Exception:
        links = []
    for a in links:
        try:
            driver.execute_script("arguments[0].scrollIntoView();", a)
            try: a.click()
            except Exception: driver.execute_script("arguments[0].click();", a)
            time.sleep(1.2)
            try:
                WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, "//input[@id='customer-email' or @type='tel']")))
                print("✅ moved to checkout via link.")
                return True
            except Exception:
                pass
        except Exception:
            continue
    # final fallback: direct GET
    try:
        driver.get(CHECKOUT_URL)
    except Exception:
        pass
    try:
        WebDriverWait(driver, WAIT*2).until(EC.presence_of_element_located((By.XPATH, "//input[@id='customer-email' or @type='tel']")))
        print("✅ checkout loaded after driver.get()")
        return True
    except Exception:
        # save debug
        try:
            with open("checkout_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("⚠️ checkout not ready — saved page to checkout_debug.html for inspection. current_url:", driver.current_url)
        except Exception:
            pass
        return False

def set_input_by_xpaths(driver, xpaths, value):
    for xp in xpaths:
        try:
            el = driver.find_element(By.XPATH, xp)
            driver.execute_script("arguments[0].scrollIntoView();", el)
            try: el.clear()
            except Exception: driver.execute_script("arguments[0].value='';", el)
            el.send_keys(value)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
            time.sleep(0.2)
            print("✅ set field via:", xp)
            return True
        except Exception:
            continue
    return False

def ensure_terms_checked(driver, wait_before_click=5, max_attempts=6):
    print(f"⏱️ سننتظر {wait_before_click} ثانية قبل محاولة النقر على مربع الشروط...")
    time.sleep(wait_before_click)
    xpaths = ["//input[@type='checkbox' and (contains(@id,'agree') or contains(@name,'agreement') or contains(@name,'agree'))]", "//input[@type='checkbox']"]
    label_text_selectors = ["//label[contains(.,'الشروط') or contains(.,'أوافق') or contains(.,'الشروط والأحكام')]", "//div[contains(.,'الشروط') or contains(.,'أوافق') or contains(.,'الشروط والأحكام')]", "//*[contains(@class,'agree') or contains(@class,'checkbox') or contains(@class,'form-check') or contains(@class,'terms')]"]
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        print(f"🔁 محاولة تفعيل الشروط رقم {attempt}/{max_attempts} ...")
        for xp in xpaths:
            try:
                cbs = driver.find_elements(By.XPATH, xp)
            except Exception:
                cbs = []
            for cb in cbs:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
                    try: cb.click()
                    except Exception:
                        try: driver.execute_script("arguments[0].click();", cb)
                        except Exception: pass
                    time.sleep(0.4)
                    try:
                        if cb.is_selected() or driver.execute_script("return !!(arguments[0].checked);", cb):
                            print("✅ مربع الشروط مفعل.")
                            return True
                    except Exception:
                        pass
                    # try JS set checked
                    try:
                        driver.execute_script("arguments[0].checked=true;arguments[0].setAttribute('checked','checked');arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", cb)
                        time.sleep(0.3)
                        if driver.execute_script("return !!(arguments[0].checked);", cb):
                            print("✅ مربع الشروط مفعل بعد JS.")
                            return True
                    except Exception:
                        pass
                except Exception:
                    continue
        # click labels
        for sel in label_text_selectors:
            try:
                els = driver.find_elements(By.XPATH, sel)
            except Exception:
                els = []
            for el in els:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    try: el.click()
                    except Exception: driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.4)
                    try:
                        pc = el.find_element(By.XPATH, ".//input[@type='checkbox']")
                        if pc and pc.is_selected():
                            print("✅ مربع الشروط مفعل بعد نقر label/div.")
                            return True
                    except Exception:
                        pass
                except Exception:
                    continue
        # visual candidates
        try:
            visual_candidates = driver.find_elements(By.CSS_SELECTOR, ".custom-checkbox, .fc-checkbox, .checkbox, .agree, .check")
        except Exception:
            visual_candidates = []
        for v in visual_candidates:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", v)
                try: v.click()
                except Exception: driver.execute_script("arguments[0].click();", v)
                time.sleep(0.4)
                try:
                    any_checked = driver.execute_script("return Array.from(document.querySelectorAll('input[type=checkbox]')).some(i=>i.checked);")
                    if any_checked:
                        print("✅ مربع الشروط مفعل بعد النقر على عنصر بصري مخصص.")
                        return True
                except Exception:
                    pass
            except Exception:
                continue
        print(f"⚠️ محاولة {attempt} لم تنجح — انتظر 0.8s ثم المحاولة التالية.")
        time.sleep(0.8)
    print("❌ فشل تفعيل مربع الشروط بعد كل المحاولات.")
    return False

def click_place_order_and_wait_success(driver, timeout=90):
    """
    يحاول النقر على زر إجراء الطلب ثم ينتظر صفحة النجاح.
    لا يُغلق السكربت هنا — سيبقى معلقًا حتى تضغط Enter.
    """
    order_attempts = 6
    clicked = False
    for i in range(order_attempts):
        print(f"🔘 محاولة الضغط على 'إجراء الطلب' ({i+1}/{order_attempts}) ...")
        order_xpaths = [
            "//button[contains(normalize-space(.),'إجراء الطلب') or contains(normalize-space(.),'أكمل الطلب') or contains(.,'إجراء الطلب')]",
            "//input[@type='submit' and (contains(@value,'إجراء الطلب') or contains(@value,'Place Order'))]",
            "//button[contains(@class,'place-order') or contains(@class,'checkout') or contains(@class,'submit-order')]"
        ]
        for xp in order_xpaths:
            try:
                btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.XPATH, xp)))
                try: btn.click()
                except Exception:
                    try: driver.execute_script("arguments[0].click();", btn)
                    except Exception: pass
                clicked = True
                print("✅ نقرنا إجراء الطلب عبر xp:", xp)
                break
            except Exception:
                continue
        if clicked:
            break
        time.sleep(0.8)

    if not clicked:
        print("⚠️ لم نتمكن من النقر على زر 'إجراء الطلب' بعد كل المحاولات.")
    else:
        # بعد النقر: ننتظر صفحة النجاح (timeout بالثواني)
        print(f"⏳ ننتظر حتى {timeout}s لظهور صفحة النجاح ({SUCCESS_URL_PART}) ...")
        try:
            WebDriverWait(driver, timeout).until(EC.url_contains(SUCCESS_URL_PART))
            print("🎉 وصلنا لصفحة النجاح URL:", driver.current_url)
            return True
        except TimeoutException:
            print("⚠️ لم تظهر صفحة النجاح خلال الوقت المحدد.")
            try:
                with open("success_debug.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("ℹ️ حفظنا success_debug.html للتشخيص. current_url:", driver.current_url)
            except Exception:
                pass
            return False

def main():
    driver = make_driver()
    try:
        print("🔗 فتح صفحة المنتج...")
        driver.get(PRODUCT_URL)
        try:
            WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except Exception:
            pass

        qty_ok = try_set_quantity(driver, TARGET_QTY)
        print("تعيين الكمية:", "نجاح" if qty_ok else "فشل")
        time.sleep(0.6)

        added = click_add_to_cart(driver)
        print("إضافة للسلة:", "نجاح" if added else "فشل")
        time.sleep(0.8)

        # إجبار الذهاب للـ checkout (يتعامل مع صفحة العربة أولاً)
        ok_checkout = force_go_to_checkout(driver)
        if not ok_checkout:
            print("❌ checkout لم يُحمل بشكل صحيح — راجع checkout_debug.html أو اطبع لي مخرجات الطرفية.")
            # لا ننهي السكربت — ننتظر منك تدخل للتشخيص
            input("اضغط Enter عندما تريد أن ننهي السكربت (أو اضغط Ctrl+C)...")
            return

        # ملء الحقول
        set_input_by_xpaths(driver, ["//input[@id='customer-email']", "//input[@type='email' and contains(@name,'email')]"], EMAIL)
        set_input_by_xpaths(driver, ["//input[@type='tel']", "//input[contains(@name,'phone') or contains(@id,'phone')]"], PHONE)
        set_input_by_xpaths(driver, ["//input[@name='firstname']", "//input[@id='firstname']"], FULL_NAME.split()[0] if FULL_NAME else "")
        if len(FULL_NAME.split())>1:
            set_input_by_xpaths(driver, ["//input[@name='lastname']", "//input[@id='lastname']"], " ".join(FULL_NAME.split()[1:]))

        # اختيار طريقة الدفع (محاولة)
        payment_selected = False
        try:
            radios = driver.find_elements(By.XPATH, "//input[@type='radio' and (contains(@name,'payment') or contains(@name,'method'))]")
            for r in radios:
                try:
                    lab_text = ""
                    try:
                        lab = r.find_element(By.XPATH, "ancestor::label[1]")
                        lab_text = lab.text or ""
                    except Exception:
                        lab_text = (r.get_attribute("aria-label") or "")
                    val = (r.get_attribute("value") or "").lower()
                    if PAYMENT_TEXT.lower() in lab_text.lower() or PAYMENT_TEXT.lower() in val or "uwallet" in val:
                        try: driver.execute_script("arguments[0].click();", r)
                        except Exception:
                            try: r.click()
                            except Exception: pass
                        payment_selected = True
                        print("✅ اخترنا طريقة الدفع:", PAYMENT_TEXT)
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # تأكد الشروط
        terms_ok = ensure_terms_checked(driver, wait_before_click=5, max_attempts=6)
        print("الموافقة على الشروط:", "تم" if terms_ok else "لم")

        # اضغط إجراء الطلب وانتظر صفحة النجاح
        success = click_place_order_and_wait_success(driver, timeout=90)
        if success:
            print("🎉 تم الوصول إلى صفحة النجاح — العملية نجحت.")
        else:
            print("⚠️ لم نصل لصفحة النجاح تلقائياً — راجع success_debug.html أو الصفحة المفتوحة في المتصفح.")

        # IMPORTANT: لا ننهي السكربت هنا — ننتظرك لتنهيه يدوياً
        print("\n========================")
        print("السكربت انتهى الإجراءات لكنه سيبقى قيد التشغيل حتى تغلقه يدوياً.")
        print("- افحص المتصفح المفتوح. إذا تريد إنهاء السكربت الآن، اذهب إلى الطرفية واضغط Enter.")
        print("========================\n")
        input("اضغط Enter في الطرفية لإغلاق المتصفح وإنهاء السكربت...")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == '__main__':
    main()
