#!/usr/bin/env python3
# success.devtools
# Fixed: robust filling for email/phone/name + force checkout + wait-for-success + keep process alive
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

# ====== helpers ======
def close_common_overlays(driver):
    # try to close cookie banners / overlays that may block inputs
    selectors = [
        "//button[contains(.,'أوافق') or contains(.,'قبول') or contains(.,'Accept')]", 
        "//button[contains(.,'إغلاق') or contains(.,'اغلاق') or contains(.,'Close')]",
        "//*[contains(@class,'modal-close') or contains(@class,'cookie') or contains(@class,'close') or contains(@class,'accept')]"
    ]
    for sel in selectors:
        try:
            elems = driver.find_elements(By.XPATH, sel)
            for e in elems:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", e)
                    try:
                        e.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", e)
                    time.sleep(0.4)
                except Exception:
                    continue
        except Exception:
            continue

def try_set_quantity(driver, qty):
    xps = ["//input[@type='number']", "//input[contains(@name,'qty') or contains(@name,'quantity') or contains(@id,'qty') or contains(@id,'quantity')]","//input[@name='quantity']"]
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
    close_common_overlays(driver)
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

# ---------- robust phone & name fillers ----------
def robust_set_phone(driver, phone):
    """Try multiple strategies to set phone (typing, intlTelInput, hidden inputs)."""
    def dispatch(el):
        try:
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}));arguments[0].dispatchEvent(new Event('change',{bubbles:true}));arguments[0].blur();", el)
        except Exception:
            pass

    local = phone
    intl = phone
    if phone.startswith("0"):
        intl = "+962" + phone.lstrip("0")
    else:
        if not phone.startswith("+"):
            intl = "+962" + phone.lstrip("0")

    xpath_candidates = [
        "//input[@type='tel']",
        "//input[contains(translate(@name,'PHONE','phone'),'phone') or contains(@name,'telephone') or contains(@id,'phone') or contains(@id,'telephone')]",
        "//input[contains(@class,'phone') or contains(@class,'tel') or contains(@class,'mobile')]",
        "//input[@placeholder and (contains(@placeholder,'+962') or contains(@placeholder,'رقم') or contains(@placeholder,'Phone'))]",
        "//input[contains(@class,'iti__input') or contains(@class,'intl') or contains(@class,'intl-tel')]",
        "//input[@name='telephone' or @name='phone' or @name='telephone_full' or @name='phoneNumber']",
        "//input[@type='text']"
    ]
    # 1) typing into visible inputs
    for xp in xpath_candidates:
        try:
            els = driver.find_elements(By.XPATH, xp)
        except Exception:
            els = []
        for el in els:
            try:
                if not el.is_displayed():
                    continue
                try: el.click()
                except Exception: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try: el.clear()
                except Exception: driver.execute_script("arguments[0].value='';", el)
                cur = ""
                try: cur = (el.get_attribute("value") or "").strip()
                except Exception: pass
                to_type = local
                if cur.startswith("+962") and local.startswith("0"):
                    to_type = local.lstrip("0")
                for ch in to_type:
                    try: el.send_keys(ch)
                    except Exception: pass
                    time.sleep(0.02)
                dispatch(el)
                time.sleep(0.25)
                val = ""
                try: val = (el.get_attribute("value") or "")
                except Exception: pass
                if local.lstrip("0") in val or local in val or "+962" in val or intl in val:
                    print("✅ تعبئة الهاتف عبر typing ناجح على xp:", xp)
                    return True
            except Exception:
                continue
    # 2) intlTelInput.setNumber
    try:
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
        res = driver.execute_script(js, intl)
        if res:
            print("✅ تعبئة الهاتف عبر intlTelInput.setNumber نجحت")
            return True
    except Exception:
        pass
    # 3) hidden inputs
    try:
        js_hidden = """
        var inputs = Array.from(document.querySelectorAll('input[name*=\"phone\"], input[name*=\"telephone\"], input[id*=\"phone\"], input[id*=\"telephone\"], input[name*=\"telephone_full\"], input[name*=\"phoneNumber\"]'));
        if(inputs.length){
          inputs.forEach(function(i){ i.value = arguments[0]; i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true})); });
          return inputs.length;
        }
        return 0;
        """
        cnt = driver.execute_script(js_hidden, intl)
        if cnt and int(cnt) > 0:
            print("✅ ضبطنا حقول الهاتف المخفية عبر JS (count):", cnt)
            return True
    except Exception:
        pass
    # 4) contenteditable fallback
    try:
        js_ce = """
        var el = Array.from(document.querySelectorAll('[contenteditable=\"true\"], [role=\"combobox\"], [role=\"textbox\"]')).find(e=> (e.innerText||'').match(/\\d{3}/));
        if(el){
          el.focus();
          el.innerText = arguments[0];
          el.dispatchEvent(new Event('input',{bubbles:true}));
          el.dispatchEvent(new Event('change',{bubbles:true}));
          return true;
        }
        return false;
        """
        res2 = driver.execute_script(js_ce, local)
        if res2:
            print("✅ تعبئة الهاتف عبر contenteditable نجحت")
            return True
    except Exception:
        pass
    print("❌ فشل تعبئة الهاتف تلقائياً")
    return False

def robust_set_name(driver, full_name):
    parts = full_name.strip().split()
    first = parts[0] if parts else full_name
    last = " ".join(parts[1:]) if len(parts) > 1 else ""
    tried = [
        (["//input[@name='firstname']", "//input[@id='firstname']", "//input[contains(@name,'first')]"], first),
        (["//input[@name='lastname']", "//input[@id='lastname']", "//input[contains(@name,'last')]"], last),
        (["//input[@name='fullname']", "//input[contains(@name,'full') or contains(@id,'fullname') or contains(@placeholder,'الاسم الكامل')]"], full_name),
        (["//input[@name='name']", "//input[contains(@id,'name') or contains(@placeholder,'الاسم') or contains(@placeholder,'Name')]"], full_name)
    ]
    any_ok = False
    for xpaths, val in tried:
        if not val:
            continue
        for xp in xpaths:
            try:
                el = driver.find_element(By.XPATH, xp)
                if el and el.is_displayed():
                    try: el.click()
                    except Exception: pass
                    try: el.clear()
                    except Exception: driver.execute_script("arguments[0].value='';", el)
                    el.send_keys(val)
                    try:
                        driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
                    except Exception:
                        pass
                    time.sleep(0.15)
                    any_ok = True
                    print("✅ ملأنا الاسم في xp:", xp)
                    break
            except Exception:
                continue
        if any_ok:
            break
    # fallback placeholder
    if not any_ok:
        try:
            el = driver.find_element(By.XPATH, "//input[contains(@placeholder,'الاسم') or contains(@placeholder,'Name') or contains(@placeholder,'الاسم الكامل')]")
            try: el.clear()
            except Exception: driver.execute_script("arguments[0].value='';", el)
            el.send_keys(full_name)
            try:
                driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
            except Exception:
                pass
            time.sleep(0.15)
            any_ok = True
            print("✅ ملأنا الاسم في placeholder-field")
        except Exception:
            pass
    if not any_ok:
        print("❌ لم نتمكن من ملء الاسم تلقائياً")
    return any_ok

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
        # click labels and visual candidates
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

        ok_checkout = force_go_to_checkout(driver)
        if not ok_checkout:
            print("❌ checkout لم يُحمل بشكل صحيح — راجع checkout_debug.html أو اطبع لي مخرجات الطرفية.")
            input("اضغط Enter عندما تريد أن ننهي السكربت (أو اضغط Ctrl+C)...")
            return

        # close overlay then fill fields (robust)
        close_common_overlays(driver)
        # Email
        email_ok = False
        for _ in range(3):
            email_ok = set_input_by_xpaths := None
            try:
                email_ok = driver.find_element(By.XPATH, "//input[@id='customer-email']")
                if email_ok:
                    try:
                        email_ok.clear()
                    except Exception:
                        driver.execute_script("arguments[0].value='';", email_ok)
                    email_ok.send_keys(EMAIL)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", email_ok)
                    print("✅ set field via: //input[@id='customer-email']")
                    break
            except Exception:
                time.sleep(0.5)
        # use robust setters for phone & name
        phone_ok = robust_set_phone(driver, PHONE)
        name_ok = robust_set_name(driver, FULL_NAME)

        # choose payment (best-effort)
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

        # agree terms
        terms_ok = ensure_terms_checked(driver, wait_before_click=5, max_attempts=6)
        print("الموافقة على الشروط:", "تم" if terms_ok else "لم")

        # place order and wait for success
        success = click_place_order_and_wait_success(driver, timeout=90)
        if success:
            print("🎉 تم الوصول إلى صفحة النجاح — العملية نجحت.")
        else:
            print("⚠️ لم نصل لصفحة النجاح تلقائياً — راجع success_debug.html أو الصفحة المفتوحة في المتصفح.")

        print("\n========================")
        print("السكربت انتهى الإجراءات ولكنه سيبقى قيد التشغيل حتى تغلقه يدوياً.")
        print("لفحص: افتح المتصفح المفتوح أو اطلع على ملفات debug (checkout_debug.html / success_debug.html).")
        print("عند الاستعداد لانهاء السكربت اضغط Enter في الطرفية.")
        print("========================\n")
        input("اضغط Enter في الطرفية لإغلاق المتصفح وإنهاء السكربت...")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == '__main__':
    main()
