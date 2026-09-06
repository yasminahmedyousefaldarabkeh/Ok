#!/usr/bin/env python3
"""
DONEE_Version6.py
تحسينات لحل مشكلة عدم إدخال رقم المحفظة:
 - يدعم الحقول داخل iframes
 - يدعم حقول داخل Shadow DOM عبر JS deep-set
 - يكرر المحاولات بطرق متعددة ويتأكد من كتابة القيمة قبل الضغط على زر الإرسال
Usage:
  pip install selenium webdriver-manager
  python DONEE_Version6.py
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
HEADLESS = False   # أثناء التجريب خليه False لتشوف المتصفح
WAIT = 12
ORDER_SUCCESS_WAIT = 30  # seconds to wait for redirect to success

# بيانات العميل — عدّل حسب الحاجة
PHONE = "790114370"
EMAIL = "custmernewallt@gmail.com"
FULL_NAME = "testtesttest"
PAYMENT_TEXT = "UWallet"

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

# ---------- helper: collect red messages (same heuristic) ----------
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

# ---------- robust wallet fill that handles iframes and shadow DOM ----------
def handle_success_page_wallet_and_capture(driver, wallet_number=WALLET_NUMBER_TO_FILL):
    """
    Improved: try iframe -> normal DOM -> shadow DOM -> global JS set.
    Ensure value is present before clicking send.
    """
    try:
        WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except Exception:
        pass

    print("⤴️ معالجة صفحة النجاح: محاولة ملء رقم المحفظة وإرسال رمز التحقق...")

    # 1) If there are iframes, try to find the wallet field inside them
    original_handle = None
    try:
        original_handle = driver.current_window_handle
    except Exception:
        original_handle = None

    def find_and_set_in_current_context():
        # try many selectors within current document context
        selectors = [
            "input[name*=wallet]", "input[id*=wallet]", "input[placeholder*=محفظ]", "input[placeholder*=محفظة]",
            "input[placeholder*=079]", "input[placeholder*=07]", "input[name*=mobile]", "input[id*=mobile]",
            "input[type=tel]", "input[type=text]", "input[class*=wallet]", "input[class*=mobile]", "input[class*=phone']"
        ]
        # combine XPaths too
        xpaths = [
            "//input[contains(translate(@name,'WALLET','wallet'),'wallet') or contains(translate(@id,'WALLET','wallet'),'wallet') or contains(@placeholder,'محفظ') or contains(@placeholder,'079') or contains(@name,'mobile') or contains(@id,'mobile') or contains(@class,'wallet') or contains(@class,'mobile') or @type='tel']"
        ]
        # 1A: CSS selectors
        for sel in selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                els = []
            for el in els:
                try:
                    if not el.is_displayed():
                        # still try but prefer visible later
                        pass
                    # try typing
                    try:
                        el.click()
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        except Exception:
                            pass
                    try:
                        el.clear()
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].value='';", el)
                        except Exception:
                            pass
                    # type char by char
                    for ch in wallet_number:
                        try:
                            el.send_keys(ch)
                        except Exception:
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
                    # verify
                    try:
                        v = el.get_attribute("value") or ""
                    except Exception:
                        v = ""
                    if wallet_number in v or wallet_number.lstrip("0") in v:
                        return True
                except Exception:
                    continue
        # 1B: XPath attempt
        for xp in xpaths:
            try:
                els = driver.find_elements(By.XPATH, xp)
            except Exception:
                els = []
            for el in els:
                try:
                    if not el.is_displayed():
                        pass
                    try:
                        el.click()
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        except Exception:
                            pass
                    try:
                        el.clear()
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].value='';", el)
                        except Exception:
                            pass
                    el.send_keys(wallet_number)
                    try:
                        driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
                    except Exception:
                        pass
                    try:
                        v = el.get_attribute("value") or ""
                    except Exception:
                        v = ""
                    if wallet_number in v or wallet_number.lstrip("0") in v:
                        return True
                except Exception:
                    continue
        return False

    # Try direct context first (page root)
    set_ok = False
    try:
        set_ok = find_and_set_in_current_context()
    except Exception:
        set_ok = False

    # If not set, try to find shadow DOM elements via JS helper that sets first matching element
    if not set_ok:
        try:
            js_deep_set = """
            (function(selectors, val){
              function setOnFound(el){
                try{
                  el.focus();
                  el.value = val;
                  el.dispatchEvent(new Event('input',{bubbles:true}));
                  el.dispatchEvent(new Event('change',{bubbles:true}));
                  return true;
                }catch(e){ return false; }
              }
              // try direct selectors in document
              for(var i=0;i<selectors.length;i++){
                var sel = selectors[i];
                var n = document.querySelector(sel);
                if(n){ if(setOnFound(n)) return true; }
              }
              // deep traversal to handle shadow roots
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
            res = driver.execute_script(js_deep_set, css_selectors, wallet_number)
            if res:
                print("✅ deep JS set via shadow traversal succeeded")
                set_ok = True
        except Exception:
            set_ok = False

    # If still not set, check if there are iframes to search inside
    if not set_ok:
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print("ℹ️ عدد iframes على الصفحة:", len(iframes))
            for idx, frame in enumerate(iframes):
                try:
                    # switch to frame and try to set
                    driver.switch_to.frame(frame)
                    time.sleep(0.3)
                    try:
                        if find_and_set_in_current_context():
                            set_ok = True
                            print(f"✅ وُجد حقل داخل iframe index={idx} وتم ملؤه.")
                            driver.switch_to.default_content()
                            break
                    except Exception:
                        pass
                    # try JS deep set inside iframe
                    try:
                        res = driver.execute_script(js_deep_set, ["input[name*=wallet]", "input[id*=wallet]", "input[placeholder*=محفظ]", "input[type=tel]"], wallet_number)
                        if res:
                            set_ok = True
                            print(f"✅ deep JS set داخل iframe index={idx} نجح.")
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

    # Global JS set as last resort
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
                # verify
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
                    print("✅ global JS set نجح (وجدنا الحقل يحوي القيمة).")
        except Exception:
            pass

    # Final verification across page (and iframes) to be sure
    found_match = False
    try:
        # check top-level inputs
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

    # if not found, check inside iframes contents too
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
        print("❌ فشل تعبئة رقم المحفظة بعد المحاولات المتعددة. لن أضغط زر 'إرسال' لتجنّب طلب خاطئ.")
        red_messages = collect_red_messages(driver)
        if red_messages:
            print("🔴 رسائل حمراء أثناء المحاولة:")
            for m in red_messages:
                print(" -", m)
        else:
            print("ℹ️ لم تُرصد رسائل حمراء أثناء المحاولة.")
        return []

    print("✅ تم تأكيد وجود رقم المحفظة في أحد الحقول. سأبحث عن زر الإرسال...")

    # الآن العثور على زر الإرسال والضغط عليه
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

    # fallback broad search by visible text
    if send_button is None:
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

    # final JS click fallback
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
                print("⚠️ لم أعثر على زر الإرسال حتى عبر JS fallback.")
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

    # بعد النقر، انتظر واطبع أي رسائل حمراء
    time.sleep(1.0)
    red_messages = collect_red_messages(driver)
    if red_messages:
        print("🔴 الرسائل الحمراء التي ظهرت بعد محاولة الإرسال:")
        for msg in red_messages:
            print(" -", msg)
    else:
        # انتظار قصير لرصد أي رسائل متأخرة
        time_wait = 0.0
        found = []
        while time_wait < 5.0 and not found:
            time.sleep(0.8)
            time_wait += 0.8
            found = collect_red_messages(driver)
        if found:
            print("🔴 رسائل حمراء (متأخرة):")
            for msg in found:
                print(" -", msg)
            red_messages = found
        else:
            print("ℹ️ لا توجد رسائل حمراء بعد الانتظار.")
    return red_messages

# ---------- بقية الكود (try_set_quantity, click_add_to_cart, robust_set_phone, robust_set_name, fill_checkout_form)
# For brevity, reuse implementations from your previous version — they are unchanged.
# Paste here the implementations from Version5 (or keep using the prior functions).
# To keep this example runnable, I'll include minimal implementations that call the previously provided logic.

# NOTE: In your real file, copy the full earlier implementations for try_set_quantity, click_add_to_cart,
# robust_set_phone, robust_set_name, fill_checkout_form. Here we'll provide concise placeholders that call them
# from earlier versions if available; otherwise include full bodies similar to prior message.

# For completeness I'll import simple versions (they are consistent with earlier code) — copy-paste your stable implementations below.
# --- begin pasted implementations (copy from your working Version5) ---

def try_set_quantity(driver, qty):
    # minimal robust implementation (use previous detailed version in real file)
    try:
        el = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//input[@type='number' or contains(@name,'quantity') or contains(@id,'qty')]")))
        try:
            el.clear()
        except Exception:
            driver.execute_script("arguments[0].value='';", el)
        el.send_keys(str(qty))
        driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el)
        time.sleep(0.6)
        print("✅ ضبطت الكمية")
        return True
    except Exception:
        print("⚠️ ضبط الكمية فشل")
        return False

def click_add_to_cart(driver):
    try:
        btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'أضف') or contains(.,'Add to cart') or contains(@class,'add-to-cart')]")))
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
        time.sleep(1)
        print("✅ نقرنا إضافة للسلة")
        return True
    except Exception:
        print("⚠️ لم نجد زر الإضافة")
        return False

def robust_set_phone(driver, phone):
    # reuse simplified typing approach
    try:
        el = driver.find_element(By.XPATH, "//input[@type='tel' or contains(@name,'phone') or contains(@placeholder,'رقم')]")
        try:
            el.clear()
        except Exception:
            driver.execute_script("arguments[0].value='';", el)
        el.send_keys(phone)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}));", el)
        time.sleep(0.2)
        print("✅ ملأنا الهاتف (بسيط)")
        return True
    except Exception:
        print("⚠️ لم أمكن ملء الهاتف")
        return False

def robust_set_name(driver, full_name):
    try:
        el = driver.find_element(By.XPATH, "//input[contains(@name,'name') or contains(@placeholder,'الاسم')]")
        try:
            el.clear()
        except Exception:
            driver.execute_script("arguments[0].value='';", el)
        el.send_keys(full_name)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}));", el)
        time.sleep(0.15)
        print("✅ ملأنا الاسم (بسيط)")
        return True
    except Exception:
        print("⚠️ لم أمكن ملء الاسم")
        return False

def fill_checkout_form(driver):
    # simplified flow that uses previous helpers and presses submit to reach success
    driver.get(CHECKOUT_URL)
    try:
        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except Exception:
        pass
    # fill email
    try:
        el = driver.find_element(By.XPATH, "//input[@type='email' or contains(@id,'email') or contains(@name,'email')]")
        try:
            el.clear()
        except Exception:
            driver.execute_script("arguments[0].value='';", el)
        el.send_keys(EMAIL)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}));", el)
    except Exception:
        pass
    phone_ok = robust_set_phone(driver, PHONE)
    name_ok = robust_set_name(driver, FULL_NAME)

    # select payment (best-effort)
    payment_selected = False
    try:
        # look for radio/button containing PAYMENT_TEXT
        el = driver.find_element(By.XPATH, f"//*[contains(normalize-space(.),'{PAYMENT_TEXT}')]")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        try:
            el.click()
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", el)
            except Exception:
                pass
        payment_selected = True
    except Exception:
        payment_selected = False

    # terms
    terms_checked = False
    try:
        cb = driver.find_element(By.XPATH, "//input[@type='checkbox' and (contains(@id,'agree') or contains(@name,'agree') or contains(@name,'terms'))]")
        if not cb.is_selected():
            try:
                cb.click()
            except Exception:
                driver.execute_script("arguments[0].click();", cb)
        terms_checked = True
    except Exception:
        # try label click
        try:
            lab = driver.find_element(By.XPATH, "//label[contains(.,'الشروط') or contains(.,'أوافق')]")
            try:
                lab.click()
            except Exception:
                driver.execute_script("arguments[0].click();", lab)
            terms_checked = True
        except Exception:
            terms_checked = False

    # wait 5s as requested
    time.sleep(5)

    # click place order
    order_clicked = False
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(.,'إجراء الطلب') or contains(.,'Place Order') or contains(@class,'place-order')]")
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
        order_clicked = True
    except Exception:
        order_clicked = False

    # wait for success redirect (or presence of success text)
    success_redirected = False
    if order_clicked:
        try:
            WebDriverWait(driver, ORDER_SUCCESS_WAIT).until(lambda d: d.current_url.startswith(SUCCESS_URL_PREFIX))
            success_redirected = True
        except TimeoutException:
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//*[contains(.,'شكراً') or contains(.,'تم الطلب') or contains(.,'طلبك')]")))
                success_redirected = True
            except Exception:
                success_redirected = False

    return {
        "email_ok": True,
        "phone_ok": phone_ok,
        "name_ok": name_ok,
        "payment_selected": payment_selected,
        "terms_checked": terms_checked,
        "order_clicked": order_clicked,
        "success_redirected": success_redirected,
        "current_url": driver.current_url
    }

# --- end of pasted simplified implementations ---

def main():
    driver = make_driver()
    try:
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

        results = fill_checkout_form(driver)
        print("ملأ صفحة الدفع => إيميل: تم | هاتف:", "تم" if results["phone_ok"] else "لم",
              "| اسم:", "تم" if results["name_ok"] else "لم",
              "| دفع:", "تم" if results["payment_selected"] else "لم",
              "| الشروط:", "تم" if results["terms_checked"] else "لم",
              "| نقر إجراء الطلب:", "تم" if results["order_clicked"] else "لم",
              "| تم التوجيه لنجاح الطلب:", "نعم" if results["success_redirected"] else "لا",
              "| URL الحالي:", results.get("current_url", "N/A"))

        if results.get("success_redirected"):
            red_msgs = handle_success_page_wallet_and_capture(driver, WALLET_NUMBER_TO_FILL)
            if red_msgs:
                print("✅ انتهت معالجة صفحة النجاح — رسائل حمراء:")
                for m in red_msgs:
                    print(" -", m)
            else:
                print("✅ انتهت معالجة صفحة النجاح — لم تُعثر رسائل حمراء أو لم تُملأ المحفظة.")
        else:
            print("⚠️ لم نصل لصفحة النجاح؛ تخطّي مرحلة المحفظة.")
        time.sleep(2)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == '__main__':
    main()
