#!/usr/bin/env python3
"""
DONEE_Version5.py
مصحح: يجمع ما بين الملء القوي لصفحة الدفع وبين آلية موثوقة لملء رقم المحفظة في صفحة النجاح.
Usage:
  pip install selenium webdriver-manager
  python DONEE_Version5.py
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

# ====== CONFIG ======
PRODUCT_URL = "https://eshop.umniah.com/ar/%D8%A8%D8%B7%D8%A7%D9%82%D8%A9-%D9%87%D8%AF%D9%8A%D8%A9-%D8%A8%D8%A8%D8%AC%D9%8A-600-%D9%8A%D9%88-%D8%B3%D9%8A.html"
CHECKOUT_URL = "https://eshop.umniah.com/ar/checkout/index/"
SUCCESS_URL_PREFIX = "https://eshop.umniah.com/ar/checkout/onepage/success/"
TARGET_QTY = 2
HEADLESS = False
WAIT = 12
ORDER_SUCCESS_WAIT = 30  # seconds to wait for redirect to success

# بيانات العميل — عدّل حسب الحاجة
PHONE = "790114370"   # ضع رقمك هنا (يمكن مع 0)
EMAIL = "custmernewallt@gmail.com"
FULL_NAME = "testtesttest"
PAYMENT_TEXT = "UWallet"  # نص طريقة الدفع للبحث عنها (مثل UWallet)

# الإعدادات الخاصة بمرحلة النجاح
WALLET_NUMBER_TO_FILL = "0791046602"
# =================================

def make_driver(headless=HEADLESS):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-gpu")
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

# ---------------------- quantity ----------------------
def try_set_quantity(driver, qty):
    xpaths = [
        "//input[@type='number' and (contains(@id,'qty') or contains(@name,'qty') or contains(@name,'quantity') or contains(@id,'quantity'))]",
        "//input[@type='number']",
        "//input[contains(@id,'qty') or contains(@name,'qty') or contains(@name,'quantity') or contains(@id,'quantity')]",
        "//input[contains(@class,'qty') or contains(@class,'quantity')]",
        "//input[@name='quantity']"
    ]
    for xp in xpaths:
        try:
            el = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, xp)))
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            try:
                el.clear()
            except Exception:
                driver.execute_script("arguments[0].value='';", el)
            el.send_keys(str(qty))
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
            time.sleep(0.6)
            print("✅ ضبطت الكمية عبر xpath:", xp)
            return True
        except Exception:
            continue
    # fallback عبر JS
    try:
        js = "var e=document.querySelector('input[name=\"quantity\"], input[name=\"qty\"], input[type=\"number\"]'); if(e){ e.value=arguments[0]; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return true; } return false;"
        res = driver.execute_script(js, qty)
        if res:
            time.sleep(0.6)
            print("✅ ضبطت الكمية عبر fallback JS")
            return True
    except Exception:
        pass
    print("⚠️ تعذّر ضبط الكمية تلقائياً — حاول يدويًا أو شاركني outerHTML للحقل.")
    return False

# ---------------------- add to cart ----------------------
def click_add_to_cart(driver):
    candidate_xps = [
        "//button[contains(normalize-space(.),'أضف إلى السلة') or contains(normalize-space(.),'أضف للسلة') or contains(normalize-space(.),'أضف إلى العربة')]",
        "//button[contains(.,'أضف') and (contains(.,'سلة') or contains(.,'عربة'))]",
        "//a[contains(normalize-space(.),'أضف إلى السلة') or (contains(.,'أضف') and contains(.,'سلة'))]",
        "//input[@type='submit' and (contains(@value,'أضف') or contains(@value,'Add'))]",
        "//button[contains(@class,'add-to-cart') or contains(@class,'add_to_cart') or contains(@id,'add-to-cart') or contains(@id,'add_to_cart')]",
        "//*[contains(@data-action,'add-to-cart') or contains(@data-role,'add-to-cart-button')]"
    ]
    for xp in candidate_xps:
        try:
            elems = driver.find_elements(By.XPATH, xp)
        except Exception:
            elems = []
        for el in elems:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try:
                    el.click()
                except (ElementClickInterceptedException, WebDriverException):
                    driver.execute_script("arguments[0].click();", el)
                time.sleep(1)
                print("✅ نقرنا على زر الإضافة (xpath):", xp)
                return True
            except Exception:
                continue
    # broad text search
    try:
        broad = driver.find_elements(By.XPATH, "//*[self::button or self::a or self::input][contains(normalize-space(.),'أضف') or contains(normalize-space(.),'اضف') or contains(normalize-space(.),'Add to cart') or contains(normalize-space(.),'Add')]")
    except Exception:
        broad = []
    for el in broad:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            try:
                el.click()
            except (ElementClickInterceptedException, WebDriverException):
                driver.execute_script("arguments[0].click();", el)
            time.sleep(1)
            print("✅ نقرنا على زر الإضافة (broad search)")
            return True
        except Exception:
            continue
    # JS fallback
    try:
        js_try = """
        var el = document.querySelector('[data-role="add-to-cart-button"], [data-action*="add-to-cart"], button.add-to-cart, a.add-to-cart, .add-to-cart');
        if(el){ el.scrollIntoView({block:'center'}); el.click(); return el.outerHTML; }
        return null;
        """
        res = driver.execute_script(js_try)
        if res:
            time.sleep(1)
            print("✅ نقرنا زر الإضافة عبر JS querySelector")
            return True
    except Exception:
        pass
    print("⚠️ لم نتمكن من العثور على زر الإضافة تلقائيًا.")
    return False

# ---------------------- robust phone ----------------------
def robust_set_phone(driver, phone):
    def dispatch_events(el):
        try:
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));"
                "arguments[0].blur();",
                el
            )
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

    for xp in xpath_candidates:
        try:
            els = driver.find_elements(By.XPATH, xp)
        except Exception:
            els = []
        for el in els:
            try:
                try:
                    if not el.is_displayed():
                        continue
                except Exception:
                    pass
                try:
                    el.click()
                except Exception:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try:
                    el.clear()
                except Exception:
                    driver.execute_script("arguments[0].value='';", el)
                cur = ""
                try:
                    cur = (el.get_attribute("value") or "").strip()
                except Exception:
                    pass
                to_type = local
                if cur.startswith("+962") and local.startswith("0"):
                    to_type = local.lstrip("0")
                for ch in to_type:
                    try:
                        el.send_keys(ch)
                    except Exception:
                        pass
                    time.sleep(0.02)
                dispatch_events(el)
                time.sleep(0.25)
                val = ""
                try:
                    val = (el.get_attribute("value") or "")
                except Exception:
                    pass
                if local.lstrip("0") in val or local in val or "+962" in val or intl in val:
                    print("✅ تعبئة الهاتف عبر typing ناجح على xp:", xp)
                    return True
            except Exception:
                continue

    # intlTelInput.setNumber via JS
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

    # hidden inputs JS
    try:
        js_hidden = """
        var inputs = Array.from(document.querySelectorAll('input[name*="phone"], input[name*="telephone"], input[id*="phone"], input[id*="telephone"], input[name*="telephone_full"], input[name*="phoneNumber"]'));
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

    # contenteditable fallback
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

# ---------------------- robust name ----------------------
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
                    try:
                        el.click()
                    except Exception:
                        pass
                    try:
                        el.clear()
                    except Exception:
                        driver.execute_script("arguments[0].value='';", el)
                    el.send_keys(val)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
                    time.sleep(0.15)
                    any_ok = True
                    print("✅ ملأنا الاسم في xp:", xp)
                    break
            except Exception:
                continue
        if any_ok:
            break
    # fallback: placeholder-based field
    if not any_ok:
        try:
            el = driver.find_element(By.XPATH, "//input[contains(@placeholder,'الاسم') or contains(@placeholder,'Name') or contains(@placeholder,'الاسم الكامل')]")
            try:
                el.clear()
            except Exception:
                driver.execute_script("arguments[0].value='';", el)
            el.send_keys(full_name)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
            time.sleep(0.15)
            any_ok = True
            print("✅ ملأنا الاسم في placeholder-field")
        except Exception:
            pass
    if not any_ok:
        print("❌ لم نتمكن من ملء الاسم تلقائياً")
    return any_ok

# ---------------------- collect red messages ----------------------
def collect_red_messages(driver):
    js = """
    (function(){
      var texts = [];
      function addIfNonEmpty(t){
        if(!t) return;
        t = t.trim();
        if(t.length) texts.push(t);
      }
      var sel = Array.from(document.querySelectorAll('.error, .errors, .invalid, .invalid-feedback, .text-danger, .alert-danger, .message--error, .form-error, .help-block.error'));
      sel.forEach(function(e){ addIfNonEmpty(e.innerText); });
      function isVisible(el){
        var r = el.getBoundingClientRect();
        return (r.width>0 && r.height>0);
      }
      var all = Array.from(document.querySelectorAll('body *'));
      for(var i=0;i<all.length;i++){
        var el = all[i];
        if(!isVisible(el)) continue;
        if(!el.innerText) continue;
        var txt = el.innerText.trim();
        if(!txt) continue;
        var s = window.getComputedStyle(el);
        if(!s) continue;
        var c = s.color || '';
        var m = c.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
        if(m){
          var r = parseInt(m[1]), g = parseInt(m[2]), b = parseInt(m[3]);
          if(r > 150 && g < 130 && b < 130){
            addIfNonEmpty(txt);
          }
        }
      }
      var uniq = texts.filter(function(v,i,a){ return a.indexOf(v) === i; });
      return uniq;
    })();
    """
    try:
        res = driver.execute_script(js)
        if isinstance(res, list):
            return [r.strip() for r in res if isinstance(r, str) and r.strip()]
    except Exception:
        pass
    return []

# ---------------------- fill checkout form ----------------------
def fill_checkout_form(driver):
    # افتح صفحة الدفع
    driver.get(CHECKOUT_URL)
    try:
        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        pass

    def set_input_by_xpaths(xpaths, value):
        for xp in xpaths:
            try:
                el = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, xp)))
                try:
                    el.click()
                except Exception:
                    pass
                try:
                    el.clear()
                except Exception:
                    driver.execute_script("arguments[0].value='';", el)
                el.send_keys(value)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
                time.sleep(0.2)
                print("✅ ملأنا حقل عبر:", xp)
                return True
            except Exception:
                continue
        return False

    # EMAIL
    email_xps = ["//input[@id='customer-email']", "//input[@type='email' and (contains(@name,'email') or contains(@id,'email'))]", "//input[contains(@placeholder,'البريد') or contains(@placeholder,'email') or contains(@name,'email')]"]
    email_ok = set_input_by_xpaths(email_xps, EMAIL)

    # PHONE (use robust function)
    phone_ok = robust_set_phone(driver, PHONE)

    # NAME (use robust function)
    name_ok = robust_set_name(driver, FULL_NAME)

    # اختر طريقة الدفع (ابحث عن radio أو label يحتوي PAYMENT_TEXT)
    payment_selected = False
    try:
        radios = driver.find_elements(By.XPATH, "//input[@type='radio' and (contains(@name,'payment') or contains(@name,'method'))]")
        for r in radios:
            try:
                label_text = ""
                try:
                    lab = r.find_element(By.XPATH, "ancestor::label[1]")
                    label_text = lab.text or ""
                except Exception:
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
                    print("✅ اخترنا طريقة الدفع عبر radio/label:", PAYMENT_TEXT)
                    break
            except Exception:
                continue
        if not payment_selected:
            labels = driver.find_elements(By.XPATH, f"//label[contains(normalize-space(.), '{PAYMENT_TEXT}')] | //span[contains(normalize-space(.), '{PAYMENT_TEXT}')] | //div[contains(normalize-space(.), '{PAYMENT_TEXT}')]")
            for lbl in labels:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", lbl)
                    payment_selected = True
                    print("✅ اخترنا طريقة الدفع عبر element containing text:", PAYMENT_TEXT)
                    break
                except Exception:
                    continue
    except Exception:
        payment_selected = False

    # اوافق على الشروط (checkbox) — نضمن أنه محدد
    terms_checked = False
    cb = None
    terms_xpaths = [
        "//input[@type='checkbox' and (contains(@id,'agree') or contains(@name,'agreement') or contains(@name,'agree'))]",
        "//label[contains(.,'الشروط') or contains(.,'أوافق') or contains(.,'الشروط والأحكام')]/preceding::input[@type='checkbox'][1]",
        "//input[@type='checkbox']"
    ]
    for xp in terms_xpaths:
        try:
            candidate = driver.find_elements(By.XPATH, xp)
        except Exception:
            candidate = []
        if not candidate:
            continue
        for element in candidate:
            try:
                try:
                    if not element.is_displayed():
                        continue
                except Exception:
                    pass
                cb = element
                try:
                    if not cb.is_selected():
                        try:
                            cb.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", cb)
                    # small wait to let page react
                    time.sleep(0.2)
                    # re-check
                    try:
                        if cb.is_selected():
                            terms_checked = True
                            print("✅ وافقنا على الشروط عبر xp:", xp)
                            break
                    except Exception:
                        # assume success if no exception
                        terms_checked = True
                        print("✅ حاولنا تفعيل الشروط عبر xp (لم نستطع التحقق) :", xp)
                        break
                except Exception:
                    continue
            except Exception:
                continue
        if terms_checked:
            break

    # If not found or not selected yet, try clicking labels/text that likely toggle checkbox
    if not terms_checked:
        try:
            possible_labels = driver.find_elements(By.XPATH, "//label[contains(.,'الشروط') or contains(.,'أوافق') or contains(.,'الشروط والأحكام')] | //a[contains(.,'الشروط') and contains(.,'الأحكام')]")
        except Exception:
            possible_labels = []
        for lbl in possible_labels:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", lbl)
                try:
                    lbl.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", lbl)
                time.sleep(0.3)
                # attempt to find checkbox inside/nearby this label
                try:
                    inside_cb = lbl.find_element(By.XPATH, ".//input[@type='checkbox']")
                    try:
                        if inside_cb.is_selected():
                            cb = inside_cb
                            terms_checked = True
                            print("✅ فعلنا الشروط بالنقر على الـ label (وجدنا checkbox داخله).")
                            break
                    except Exception:
                        terms_checked = True
                        cb = inside_cb
                        print("✅ فعلنا الشروط بالنقر على الـ label (لم نتحقق من الحالة).")
                        break
                except Exception:
                    # try to locate a checkbox immediately preceding/following label in DOM
                    try:
                        nearby_cb = lbl.find_element(By.XPATH, "(.//preceding::input[@type='checkbox']|.//following::input[@type='checkbox'])[1]")
                        try:
                            if nearby_cb.is_selected():
                                cb = nearby_cb
                                terms_checked = True
                                print("✅ فعلنا الشروط بالنقر على الـ label (checkbox مجاور محدد).")
                                break
                        except Exception:
                            terms_checked = True
                            cb = nearby_cb
                            print("✅ فعلنا الشروط بالنقر على الـ label (checkbox مجاور، حالة غير مؤكدة).")
                            break
                    except Exception:
                        # continue to next label
                        continue
            except Exception:
                continue

    # الآن نضمن الانتظار 5 ثواني قبل الإجراء (حسب طلبك)
    if terms_checked:
        try:
            if cb is not None:
                try:
                    if not cb.is_selected():
                        try:
                            cb.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", cb)
                except Exception:
                    pass
            print("✅ الشروط مفعّلة، سننتظر 5 ثواني قبل إجراء الطلب...")
        except Exception:
            print("⚠️ تعذّر التحقق من حالة الـ checkbox بعد تحديده — سننتظر 5 ثواني ثم نستمر")
        time.sleep(5)
    else:
        print("⚠️ لم يتم تحديد الـ checkbox تلقائياً — سننتظر 5 ثواني ثم نحاول إجراء الطلب على أي حال")
        time.sleep(5)

    # اضغط إجراء الطلب ثم انتظر إعادة التوجيه للصفحة الناجحة
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
            print("✅ نقرنا إجراء الطلب عبر xp:", xp)
            break
        except Exception:
            continue

    success_redirected = False
    if order_clicked:
        try:
            WebDriverWait(driver, ORDER_SUCCESS_WAIT).until(lambda d: d.current_url.startswith(SUCCESS_URL_PREFIX))
            print("✅ تم التوجيه إلى صفحة النجاح:", driver.current_url)
            success_redirected = True
        except TimeoutException:
            # محاولة اكتشاف صفحة النجاح عبر عناصر الصفحة
            try:
                WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//*[contains(.,'شكراً') or contains(.,'تم الطلب') or contains(.,'طلبك')][1]")))
                print("⚠️ لم يتغيّر URL لكن وجدنا نص نجاح محتمل في الصفحة. URL الحالي:", driver.current_url)
                success_redirected = True
            except Exception:
                print("⚠️ لم يتم التوجيه إلى صفحة النجاح خلال المهلة. URL الحالي:", driver.current_url)
    else:
        print("⚠️ لم نتمكن من النقر على زر إجراء الطلب.")

    return {
        "email_ok": email_ok,
        "phone_ok": phone_ok,
        "name_ok": name_ok,
        "payment_selected": payment_selected,
        "terms_checked": terms_checked,
        "order_clicked": order_clicked,
        "success_redirected": success_redirected,
        "current_url": driver.current_url
    }

# ---------------------- improved wallet handling (iframe + shadow support) ----------------------
def handle_success_page_wallet_and_capture(driver, wallet_number=WALLET_NUMBER_TO_FILL):
    """
    Try to write wallet_number into any reasonable wallet input, handling:
      - direct DOM inputs
      - shadow DOM via a deep JS setter
      - inputs inside iframes (switching temporarily)
    Ensure the value is present before clicking "send code".
    Collect and print red messages after clicking (or if not clicked).
    """
    try:
        WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except Exception:
        pass

    print("⤴️ معالجة صفحة النجاح: محاولة ملء رقم المحفظة وإرسال رمز التحقق...")
    # helper to attempt set in current context
    def set_in_current_context():
        # try a series of XPath/CSS to find likely inputs
        xps = [
            "//input[contains(translate(@name,'WALLET','wallet'),'wallet') or contains(translate(@id,'WALLET','wallet'),'wallet') or contains(@placeholder,'محفظ') or contains(@placeholder,'079') or contains(@name,'mobile') or contains(@id,'mobile') or contains(@class,'wallet') or @type='tel' or @type='text']",
            "//input[contains(@placeholder,'07') or contains(@placeholder,'079') or contains(@placeholder,'+962')]",
            "//input[contains(@name,'wallet') or contains(@id,'wallet') or contains(@name,'uwallet') or contains(@id,'uwallet')]"
        ]
        for xp in xps:
            try:
                els = driver.find_elements(By.XPATH, xp)
            except Exception:
                els = []
            for el in els:
                try:
                    # try to interact
                    try:
                        if not el.is_displayed():
                            pass
                    except Exception:
                        pass
                    try:
                        el.click()
                    except Exception:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    try:
                        el.clear()
                    except Exception:
                        driver.execute_script("arguments[0].value='';", el)
                    # type char-by-char
                    for ch in wallet_number:
                        try:
                            el.send_keys(ch)
                        except Exception:
                            # fallback append
                            try:
                                driver.execute_script("arguments[0].value = (arguments[0].value || '') + arguments[1];", el, ch)
                            except Exception:
                                pass
                        time.sleep(0.02)
                    # dispatch events
                    try:
                        driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
                    except Exception:
                        pass
                    time.sleep(0.2)
                    try:
                        v = el.get_attribute("value") or ""
                    except Exception:
                        v = ""
                    if wallet_number in v or wallet_number.lstrip("0") in v:
                        return True
                except Exception:
                    continue
        return False

    # 1) direct attempt
    set_ok = False
    try:
        set_ok = set_in_current_context()
    except Exception:
        set_ok = False

    # 2) deep shadow DOM set via JS
    if not set_ok:
        try:
            js_deep = """
            (function(selectors, val){
              function setOnFound(el){
                try{
                  el.focus();
                  el.value = val;
                  el.dispatchEvent(new Event('input',{bubbles:true}));
                  el.dispatchEvent(new Event('change',{bubbles:true}));
                  return true;
                }catch(e){
                  return false;
                }
              }
              for(var i=0;i<selectors.length;i++){
                var n = document.querySelector(selectors[i]);
                if(n){ if(setOnFound(n)) return true; }
              }
              function walk(root){
                var nodes = root.querySelectorAll('*');
                for(var i=0;i<nodes.length;i++){
                  var node = nodes[i];
                  for(var j=0;j<selectors.length;j++){
                    try{
                      if(node.matches && node.matches(selectors[j])){
                        if(setOnFound(node)) return true;
                      }
                    }catch(e){}
                  }
                  if(node.shadowRoot){
                    var found = walk(node.shadowRoot);
                    if(found) return true;
                  }
                }
                return false;
              }
              return walk(document);
            })(arguments[0], arguments[1]);
            """
            css_selectors = ["input[name*=wallet]", "input[id*=wallet]", "input[placeholder*=محفظ]", "input[placeholder*=079]", "input[type=tel]"]
            res = driver.execute_script(js_deep, css_selectors, wallet_number)
            if res:
                print("✅ deep JS (shadow) set succeeded")
                set_ok = True
        except Exception:
            set_ok = set_ok

    # 3) try inside iframes
    if not set_ok:
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print("ℹ️ عدد iframes على الصفحة:", len(iframes))
            for idx, frame in enumerate(iframes):
                try:
                    driver.switch_to.frame(frame)
                    time.sleep(0.3)
                    try:
                        if set_in_current_context():
                            set_ok = True
                            print(f"✅ ملء المحفظة داخل iframe index={idx} نجح.")
                            driver.switch_to.default_content()
                            break
                    except Exception:
                        pass
                    # try shadow inside iframe
                    try:
                        res = driver.execute_script(js_deep, ["input[name*=wallet]","input[id*=wallet]","input[placeholder*=محفظ]"], wallet_number)
                        if res:
                            set_ok = True
                            print(f"✅ deep JS inside iframe index={idx} نجح.")
                            driver.switch_to.default_content()
                            break
                    except Exception:
                        pass
                    driver.switch_to.default_content()
                except Exception:
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
                    continue
        except Exception:
            pass

    # 4) global JS assign as last resort
    if not set_ok:
        try:
            js_global = """
            (function(val){
              var sels = ['input[name*=wallet]','input[id*=wallet]','input[placeholder*=محفظ]','input[placeholder*=079]','input[name*=mobile]','input[id*=mobile]','input[type=tel]','input[type=text]'];
              var nodes = [];
              sels.forEach(function(s){ Array.from(document.querySelectorAll(s)).forEach(function(n){ nodes.push(n); }); });
              if(nodes.length===0) nodes = Array.from(document.querySelectorAll('input'));
              nodes.forEach(function(n){
                try{ n.value = val; n.dispatchEvent(new Event('input',{bubbles:true})); n.dispatchEvent(new Event('change',{bubbles:true})); }catch(e){}
              });
              return nodes.length;
            })(arguments[0]);
            """
            cnt = driver.execute_script(js_global, wallet_number)
            if cnt and int(cnt) > 0:
                time.sleep(0.3)
                # verify presence
                try:
                    inputs = driver.find_elements(By.XPATH, "//input")
                    for e in inputs:
                        try:
                            v = e.get_attribute("value") or ""
                            if wallet_number in v or wallet_number.lstrip("0") in v:
                                set_ok = True
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
                if set_ok:
                    print("✅ global JS set نجح.")
        except Exception:
            pass

    # final verify across page and iframes
    found_match = False
    try:
        for e in driver.find_elements(By.XPATH, "//input"):
            try:
                v = (e.get_attribute("value") or "")
                if wallet_number in v or wallet_number.lstrip("0") in v:
                    found_match = True
                    break
            except Exception:
                continue
    except Exception:
        pass
    if not found_match:
        try:
            for frame in driver.find_elements(By.TAG_NAME, "iframe"):
                try:
                    driver.switch_to.frame(frame)
                    for e in driver.find_elements(By.XPATH, "//input"):
                        try:
                            v = (e.get_attribute("value") or "")
                            if wallet_number in v or wallet_number.lstrip("0") in v:
                                found_match = True
                                break
                        except Exception:
                            continue
                    driver.switch_to.default_content()
                    if found_match:
                        break
                except Exception:
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
                    continue
        except Exception:
            pass

    if not found_match:
        print("❌ فشل تعبئة رقم المحفظة بعد كل المحاولات. لن أضغط زر 'إرسال' لتجنُّب إرسال طلب ناقص.")
        red_messages = collect_red_messages(driver)
        if red_messages:
            print("🔴 رسائل حمراء أثناء المحاولة:")
            for m in red_messages:
                print(" -", m)
        else:
            print("ℹ️ لا توجد رسائل حمراء أثناء المحاولة.")
        return []

    print("✅ تأكدنا وجود رقم المحفظة في حقل ما — الآن البحث عن زر 'إرسال رمز'...")

    # العثور على زر الإرسال
    send_button = None
    send_xpaths = [
        "//button[contains(normalize-space(.),'إرسال رمز') or contains(normalize-space(.),'إرسال رمز التحقق') or (contains(normalize-space(.),'إرسال') and contains(normalize-space(.),'رمز'))]",
        "//a[contains(normalize-space(.),'إرسال رمز') or contains(normalize-space(.),'إرسال')]",
        "//button[contains(@class,'send') or contains(@class,'verify') or contains(@class,'send-code') or contains(@class,'verify-send')]",
        "//input[@type='button' and (contains(@value,'إرسال') or contains(@value,'Send'))]"
    ]
    for xp in send_xpaths:
        try:
            elems = driver.find_elements(By.XPATH, xp)
        except Exception:
            elems = []
        for el in elems:
            try:
                if el.is_displayed():
                    send_button = el
                    break
            except Exception:
                continue
        if send_button:
            break

    if send_button is None:
        # broad text fallback
        try:
            candidates = driver.find_elements(By.XPATH, "//*[self::button or self::a or self::input][contains(normalize-space(.),'إرسال') or contains(normalize-space(.),'رمز') or contains(normalize-space(.),'Send') or contains(normalize-space(.),'Verify')]")
        except Exception:
            candidates = []
        for el in candidates:
            try:
                txt = (el.text or el.get_attribute("value") or "").strip()
                if not txt:
                    continue
                if ("إرسال" in txt or "رمز" in txt or "Send" in txt or "Verify" in txt) and el.is_displayed():
                    send_button = el
                    break
            except Exception:
                continue

    # final JS click fallback if still None
    if send_button is None:
        try:
            js_click = """
            (function(){
              var candidates = Array.from(document.querySelectorAll('button, a, input'));
              for(var i=0;i<candidates.length;i++){
                var el = candidates[i];
                var txt = (el.innerText||el.value||'').trim();
                if(!txt) continue;
                if(txt.indexOf('إرسال')!==-1 || txt.indexOf('رمز')!==-1 || txt.indexOf('Send')!==-1 || txt.indexOf('Verify')!==-1){
                  try{ el.scrollIntoView({block:'center'}); el.click(); return true; }catch(e){}
                }
              }
              return false;
            })();
            """
            clicked = driver.execute_script(js_click)
            if clicked:
                print("✅ نقر JS fallback لزر الإرسال.")
            else:
                print("⚠️ لم أتمكن من العثور على زر الإرسال حتى عبر JS fallback.")
        except Exception:
            print("⚠️ خطأ أثناء محاولة JS click fallback.")
    else:
        try:
            try:
                send_button.click()
            except Exception:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", send_button)
            print("✅ نقرنا زر 'إرسال رمز التحقق'.")
        except Exception as e:
            print("⚠️ فشل النقر على زر الإرسال:", e)

    # بعد النقر، اجمع الرسائل الحمراء
    time.sleep(1.0)
    red_messages = collect_red_messages(driver)
    if red_messages:
        print("🔴 الرسائل الحمراء التي ظهرت بعد محاولة الإرسال:")
        for msg in red_messages:
            print(" -", msg)
    else:
        # انتظار قصير لرصد أي رسائل متأخرة
        found = []
        wait_time = 0.0
        while wait_time < 5.0 and not found:
            time.sleep(0.8)
            wait_time += 0.8
            found = collect_red_messages(driver)
        if found:
            print("🔴 رسائل حمراء (متأخرة):")
            for msg in found:
                print(" -", msg)
            red_messages = found
        else:
            print("ℹ️ لا توجد رسائل حمراء بعد الانتظار.")
    return red_messages

# ---------------------- main ----------------------
def main():
    driver = make_driver()
    try:
        # صفحة المنتج
        driver.get(PRODUCT_URL)
        try:
            WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            pass

        qty_ok = try_set_quantity(driver, TARGET_QTY)
        print("تعيين الكمية:", "نجاح" if qty_ok else "فشل")

        time.sleep(0.6)

        added = click_add_to_cart(driver)
        print("إضافة للسلة:", "نجاح" if added else "فشل")

        # اذهب للـ checkout وعبّي الحقول
        results = fill_checkout_form(driver)
        print("ملأ صفحة الدفع => إيميل:", "تم" if results["email_ok"] else "لم",
              "| هاتف:", "تم" if results["phone_ok"] else "لم",
              "| اسم:", "تم" if results["name_ok"] else "لم",
              "| دفع:", "تم" if results["payment_selected"] else "لم",
              "| الشروط:", "تم" if results["terms_checked"] else "لم",
              "| نقر إجراء الطلب:", "تم" if results["order_clicked"] else "لم",
              "| تم التوجيه لنجاح الطلب:", "نعم" if results["success_redirected"] else "لا",
              "| URL الحالي:", results.get("current_url", "N/A"))

        # إذا تم التوجيه لصفحة النجاح — نفّذ خطوات المحفظة والتحقق
        if results.get("success_redirected"):
            red_msgs = handle_success_page_wallet_and_capture(driver, WALLET_NUMBER_TO_FILL)
            if red_msgs:
                print("✅ انتهت معالجة صفحة النجاح — تم العثور على رسائل حمراء وأُظهرت أعلاه.")
            else:
                print("✅ انتهت معالجة صفحة النجاح — لم تُعثر رسائل حمراء أو لم يتم ملء الحقل.")
        else:
            print("⚠️ لم نصل لصفحة النجاح؛ تخطّي مرحلة المحفظة.")

        # بيسمح لك رؤية النتيجة لحظياً
        time.sleep(2)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == '__main__':
    main()
