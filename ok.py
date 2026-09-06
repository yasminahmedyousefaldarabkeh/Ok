#!/usr/bin/env python3
# selenium_umniah_ready.py
# Requirements:
#   pip install selenium webdriver-manager
# Usage:
#   python selenium_umniah_ready.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import html

PRODUCT_URL = "https://eshop.umniah.com/ar/%D8%A8%D8%B7%D8%A7%D9%82%D8%A9-%D9%87%D8%AF%D9%8A%D8%A9-%D8%A8%D8%A8%D8%AC%D9%8A-600-%D9%8A%D9%88-%D8%B3%D9%8A.html"
CHECKOUT_URL = "https://eshop.umniah.com/ar/checkout/index/"
TARGET_QTY = 2

# customer data (from your request)
PHONE = "0790114370"   # ضع رقمك هنا (مثال مع 0 بالبداية) — الدالة ستحاول إزالة الصفر لو الحقل فيه +962
EMAIL = "custmernewallet@gmail.com"
FULL_NAME = "testtesttest"
PAYMENT_TEXT = "UWallet"  # used to match label/value text
WAIT_TIMEOUT = 10  # seconds (adjust if needed)

def make_driver(headless=False):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-gpu")
    # disable images to speed up loading
    prefs = {"profile.managed_default_content_settings.images": 2}
    opts.add_experimental_option("prefs", prefs)
    # faster page load strategy
    try:
        opts.page_load_strategy = "eager"
    except Exception:
        opts.set_capability("pageLoadStrategy", "eager")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_window_size(1200, 900)
    return driver

def try_set_quantity(driver, qty):
    # multiple candidate selectors; set via JS for speed
    xpaths = [
        "//input[@type='number' and (contains(@id,'qty') or contains(@name,'qty') or contains(@name,'quantity') or contains(@id,'quantity'))]",
        "//input[@type='number']",
        "//input[contains(@id,'qty') or contains(@name,'qty') or contains(@name,'quantity') or contains(@id,'quantity')]",
    ]
    for xp in xpaths:
        try:
            el = driver.find_element(By.XPATH, xp)
            driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
                el, str(qty)
            )
            # small wait to allow page JS to react
            time.sleep(0.6)
            print("✅ ضبطت الكمية عبر:", xp)
            return True
        except Exception:
            continue

    # try plus button
    try:
        plus = driver.find_element(By.XPATH, "//button[contains(@class,'plus') or contains(@class,'increment') or contains(.,'+') or contains(@aria-label,'increase')]")
        for _ in range(qty - 1):
            try:
                plus.click()
            except Exception:
                driver.execute_script("arguments[0].click();", plus)
            time.sleep(0.25)
        print("✅ ضبطت الكمية عبر زر الزيادة")
        return True
    except Exception:
        pass

    # fallback: set by name attr
    try:
        driver.execute_script(
            "var e=document.querySelector('input[name=\"quantity\"], input[name=\"qty\"]'); if(e){ e.value=arguments[0]; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); }",
            qty
        )
        time.sleep(0.6)
        print("✅ ضبطت الكمية عبر fallback")
        return True
    except Exception:
        pass

    print("⚠️ تعذّر ضبط الكمية — حاول يدويًا أو شاركني DOM الخاص بالحقل.")
    return False

def click_add_to_cart(driver):
    """
    Robust add-to-cart:
    - try many xpaths for buttons/links/inputs
    - try JS click, scrollIntoView, submit containing form
    - create add_to_cart_candidates.html with attempted elements if fails
    """
    tried = []
    # specific candidate xpaths
    candidate_xps = [
        "//button[contains(normalize-space(.),'أضف إلى السلة') or contains(normalize-space(.),'أضف للسلة') or contains(normalize-space(.),'أضف إلى العربة')]",
        "//button[contains(.,'أضف') and (contains(.,'سلة') or contains(.,'عربة'))]",
        "//a[contains(normalize-space(.),'أضف إلى السلة') or (contains(.,'أضف') and contains(.,'سلة'))]",
        "//input[@type='submit' and (contains(@value,'أضف') or contains(@value,'Add'))]",
        "//button[contains(@class,'add-to-cart') or contains(@class,'add_to_cart') or contains(@id,'add-to-cart') or contains(@id,'add_to_cart')]",
        "//*[contains(@data-action,'add-to-cart') or contains(@data-role,'add-to-cart-button')]"
    ]

    # try each xpath, try to click each found element
    for xp in candidate_xps:
        try:
            elems = driver.find_elements(By.XPATH, xp)
        except Exception:
            elems = []
        for el in elems:
            outer = el.get_attribute("outerHTML") or el.tag_name
            tried.append(outer)
            try:
                # ensure visible / scroll to it
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try:
                    el.click()
                except (ElementClickInterceptedException, WebDriverException):
                    # fallback to JS click
                    driver.execute_script("arguments[0].click();", el)
                print("✅ نقرنا على زر الإضافة إلى السلة (إحدى المحاولات)")
                time.sleep(0.8)  # wait for cart update
                return True
            except Exception:
                # try submitting ancestor form if exists
                try:
                    ok = driver.execute_script("var f = arguments[0].closest('form'); if(f){ f.submit(); return true } return false;", el)
                    if ok:
                        print("✅ أرسلنا نموذج إضافة للسلة عبر form.submit()")
                        time.sleep(0.8)
                        return True
                except Exception:
                    continue

    # broad candidate search by text ('أضف' or 'Add')
    try:
        broad = driver.find_elements(By.XPATH, "//*[self::button or self::a or self::input][contains(normalize-space(.),'أضف') or contains(normalize-space(.),'اضف') or contains(normalize-space(.),'Add to cart') or contains(normalize-space(.),'Add')]")
    except Exception:
        broad = []
    for el in broad:
        outer = el.get_attribute("outerHTML") or el.tag_name
        tried.append(outer)
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            try:
                el.click()
            except (ElementClickInterceptedException, WebDriverException):
                driver.execute_script("arguments[0].click();", el)
            print("✅ نقرنا على زر الإضافة (broad search)")
            time.sleep(0.8)
            return True
        except Exception:
            try:
                ok = driver.execute_script("var f = arguments[0].closest('form'); if(f){ f.submit(); return true } return false;", el)
                if ok:
                    print("✅ أرسلنا نموذج إضافة للسلة عبر broad form.submit()")
                    time.sleep(0.8)
                    return True
            except Exception:
                continue

    # JS attempt for common data-role / classes
    try:
        js_try = """
        var el = document.querySelector('[data-role=\"add-to-cart-button\"], [data-action*=\"add-to-cart\"], button.add-to-cart, a.add-to-cart');
        if(el){ el.scrollIntoView({block:'center'}); el.click(); return el.outerHTML; }
        return null;
        """
        res = driver.execute_script(js_try)
        if res:
            tried.append(res)
            print("✅ نقرنا زر الإضافة عبر JS querySelector")
            time.sleep(0.8)
            return True
    except Exception:
        pass

    # write debug file listing candidates we tried to help you inspect
    try:
        with open("add_to_cart_candidates.html", "w", encoding="utf-8") as f:
            f.write("<!doctype html><meta charset='utf-8'><h2>add_to_cart candidates</h2>\n")
            for t in tried:
                f.write("<div style='border:1px solid #ddd;margin:8px;padding:8px'><pre>{}</pre></div>\n".format(html.escape(t)))
        print("ℹ️ لم نتمكن من النقر على زر الإضافة تلقائياً — أنشأنا ملف add_to_cart_candidates.html للمراجعة.")
    except Exception:
        print("⚠️ فشل إنشاء ملف التصحيح (add_to_cart_candidates.html).")

    return False

def set_tel_by_typing(driver, xpaths, value):
    """
    Reliable way to fill phone inputs:
    - tries given xpaths (string or list)
    - uses send_keys char by char so input-mask / intlTelInput reacts
    - if input shows +962 and value starts with 0, remove leading 0
    - fallback: try intl-tel-input API via JS setNumber
    """
    if isinstance(xpaths, str):
        xpaths = [xpaths]
    for xp in xpaths:
        try:
            el = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.XPATH, xp)))
            # focus & clear
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            try:
                el.clear()
            except Exception:
                driver.execute_script("arguments[0].value = '';", el)
            # if the field already shows +962 and value starts with 0, strip the 0
            try:
                cur = (el.get_attribute("value") or "").strip()
            except Exception:
                cur = ""
            val = value
            if cur.startswith("+962") and val.startswith("0"):
                # remove the leading zero so combined becomes +9627...
                val = val.lstrip("0")
            # type slowly so masks pick it up
            for ch in val:
                el.send_keys(ch)
                time.sleep(0.03)
            # dispatch input/change to ensure listeners run
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true})); arguments[0].blur();", el)
            time.sleep(0.3)
            return True
        except Exception:
            continue

    # fallback: try intlTelInput API (if page has it)
    try:
        num = value
        if num.startswith("0"):
            # try building full international with +962 if the page uses Jordan country
            # but don't assume: this is a reasonable fallback
            num = "+962" + num.lstrip("0")
        js = """
        var input = document.querySelector('input[type=\"tel\"], input[name*=\"phone\"], input[id*=\"phone\"]');
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
            print("ℹ️ setNumber عبر intlTelInput (fallback) نتيجته:", res)
            return True
    except Exception:
        pass

    return False

def fill_checkout_form(driver):
    driver.get(CHECKOUT_URL)
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        print("⚠️ صفحة الدفع استغرقت وقتاً طويلاً في التحميل — سنحاول المتابعة.")

    def set_input_by_xpaths(xpaths, value):
        for xp in xpaths:
            try:
                el = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, xp)))
                driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el, value)
                return True
            except Exception:
                continue
        return False

    # Email (index.devtools shows id=customer-email)
    email_ok = set_input_by_xpaths(["//input[@id='customer-email']", "//input[@type='email' and (contains(@name,'email') or contains(@id,'email'))]"], EMAIL)
    print("📧 الإيميل:", "تم" if email_ok else "لم يُعثر")

    # Phone - now use typing method (reliable with masks)
    phone_ok = set_tel_by_typing(driver, ["//input[@type='tel']", "//input[contains(@name,'phone') or contains(@name,'telephone') or contains(@id,'telephone')]", "//input[contains(@class,'phone') or contains(@class,'tel')]"], PHONE)
    print("📱 الهاتف:", "تم" if phone_ok else "لم يُعثر")

    # Firstname / Lastname or fullname
    parts = FULL_NAME.strip().split()
    first = parts[0] if parts else FULL_NAME
    last = " ".join(parts[1:]) if len(parts) > 1 else ""
    fn_ok = set_input_by_xpaths(["//input[@name='firstname']", "//input[contains(@id,'firstname') or contains(@name,'first')]", "//input[@id='firstname']"], first)
    ln_ok = set_input_by_xpaths(["//input[@name='lastname']", "//input[contains(@id,'lastname') or contains(@name,'last')]", "//input[@id='lastname']"], last)
    if not (fn_ok or ln_ok):
        name_ok = set_input_by_xpaths(["//input[contains(@placeholder,'الاسم') or contains(@placeholder,'الاسم الكامل') or contains(@name,'fullname') or contains(@id,'fullname')]"], FULL_NAME)
        print("👤 الاسم:", "تم" if name_ok else "لم يُعثر")
    else:
        print("👤 الاسم (fname/lname):", "تم" if (fn_ok or ln_ok) else "لم يُعثر")

    # Select payment method - look for inputs named payment[method]
    payment_selected = False
    try:
        radios = driver.find_elements(By.XPATH, "//input[@name='payment[method]']")
        for r in radios:
            try:
                # get surrounding label text if exists
                label_text = ""
                try:
                    label = r.find_element(By.XPATH, "ancestor::label[1]")
                    label_text = label.text or ""
                except Exception:
                    # try aria-label or following-sibling text
                    label_text = (r.get_attribute("aria-label") or "")
                val = (r.get_attribute("value") or "").lower()
                if PAYMENT_TEXT.lower() in label_text.lower() or PAYMENT_TEXT.lower() in val or "uwallet" in val or "prepaid" in val:
                    try:
                        driver.execute_script("arguments[0].click();", r)
                    except Exception:
                        try:
                            r.click()
                        except Exception:
                            pass
                    payment_selected = True
                    break
            except Exception:
                continue

        if not payment_selected:
            # fallback: click label or span that contains PAYMENT_TEXT
            labels = driver.find_elements(By.XPATH, f"//label[contains(normalize-space(.), '{PAYMENT_TEXT}')] | //span[contains(normalize-space(.), '{PAYMENT_TEXT}')] | //div[contains(normalize-space(.), '{PAYMENT_TEXT}')]")
            for lbl in labels:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", lbl)
                    payment_selected = True
                    break
                except Exception:
                    continue
    except Exception:
        payment_selected = False

    print("💳 اختيار UWallet:", "تم" if payment_selected else "لم يُعثر")

    # Accept terms (checkbox)
    terms_checked = False
    terms_xpaths = [
        "//input[@type='checkbox' and (contains(@id,'agree') or contains(@name,'agreement') or contains(@name,'agree'))]",
        "//label[contains(.,'الشروط') or contains(.,'أوافق') or contains(.,'الشروط والأحكام')]/preceding::input[@type='checkbox'][1]",
        "//input[@type='checkbox']"
    ]
    for xp in terms_xpaths:
        try:
            cb = driver.find_element(By.XPATH, xp)
            if not cb.is_selected():
                try:
                    cb.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", cb)
            terms_checked = True
            break
        except Exception:
            continue
    print("✅ الموافقة على الشروط:", "تم" if terms_checked else "لم يُعثر")

    # Click place order (إجراء الطلب)
    order_clicked = False
    order_xpaths = [
        "//button[contains(normalize-space(.),'إجراء الطلب') or contains(normalize-space(.),'أكمل الطلب') or contains(.,'إجراء الطلب')]",
        "//input[@type='submit' and (contains(@value,'إجراء الطلب') or contains(@value,'Place Order'))]",
        "//button[contains(@class,'place-order') or contains(@class,'checkout') or contains(@class,'submit-order')]"
    ]
    for xp in order_xpaths:
        try:
            btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable((By.XPATH, xp)))
            try:
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)
            order_clicked = True
            break
        except Exception:
            continue
    print("🚀 إجراء الطلب:", "تم النقر" if order_clicked else "لم يُنقر (راجع selector)")

    # wait for success message or redirect to gateway
    try:
        succ = WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.XPATH, "//*[contains(.,'شكراً') or contains(.,'تم الطلب') or contains(.,'Order received') or contains(.,'success')]")))
        print("🎉 تم تنفيذ الطلب - رسالة تأكيد:", (succ.text or "")[:300])
    except TimeoutException:
        print("ℹ️ لم يظهر نص تأكيد ضمن الوقت المحدد؛ قد يكون التحويل لبوابة الدفع لاحقًا.")

def main():
    driver = make_driver(headless=False)  # اجعل True لتشغيل بدون نافذة
    try:
        print("🔗 افتح صفحة المنتج...")
        driver.get(PRODUCT_URL)
        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            print("⚠️ تحميل الصفحة استغرق وقتًا — سنحاول المتابعة...")

        # set quantity
        ok_qty = try_set_quantity(driver, TARGET_QTY)
        print("النتيجة: تعيين الكمية ->", "نجاح" if ok_qty else "فشل")

        # small pause to let JS react
        time.sleep(0.6)

        # click add to cart
        added = click_add_to_cart(driver)
        print("النتيجة: إضافة للسلة ->", "نجاح" if added else "فشل")

        # proceed to fill checkout regardless (in case cart updated)
        fill_checkout_form(driver)

        # let user inspect
        time.sleep(2)
    finally:
        print("🔚 أنهى السكربت، إغلاق المتصفح.")
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
