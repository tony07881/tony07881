"""Synthetic-only Android integration probe: user-initiated Hindi model preparation.

This generates tests for the real Android SpeechRecognizer provider. It never
records audio and never asserts that a download, Hindi transcription, or Samsung
device validation succeeded merely because a request was dispatched.
"""
from pathlib import Path
p=Path('android-shell/project/app/src/androidTest/java/com/shift/systemsafe/SpeechModelDownloadProbeTest.java')
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(r'''package com.shift.systemsafe;

import android.os.SystemClock;
import android.speech.SpeechRecognizer;
import android.webkit.WebView;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.json.JSONObject;
import org.json.JSONTokener;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import java.lang.reflect.Field;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class SpeechModelDownloadProbeTest {
  private ActivityScenario<MainActivity> scenario;
  private MainActivity activity;
  private WebView web;
  private void ui(Runnable action) {
    InstrumentationRegistry.getInstrumentation().runOnMainSync(action);
  }
  private Object field(String name) throws Exception {
    Field f=MainActivity.class.getDeclaredField(name);f.setAccessible(true);
    return f.get(activity);
  }
  private Object js(String expression) throws Exception {
    CountDownLatch latch=new CountDownLatch(1);
    AtomicReference<String> value=new AtomicReference<>();
    ui(()->web.evaluateJavascript("JSON.stringify("+expression+")",v->{value.set(v);latch.countDown();}));
    assertTrue("WebView JavaScript callback",latch.await(7,TimeUnit.SECONDS));
    Object first=new JSONTokener(value.get()).nextValue();
    if(first==JSONObject.NULL)return JSONObject.NULL;
    return new JSONTokener((String)first).nextValue();
  }
  private void request(String id,String method,JSONObject args)throws Exception{
    js("(S3Native.request("+JSONObject.quote(id)+","+JSONObject.quote(method)+","+JSONObject.quote(args.toString())+"),true)");
  }
  private JSONObject response(String id,long maxMilliseconds)throws Exception{
    for(long elapsed=0;elapsed<maxMilliseconds;elapsed+=200){
      Object r=js("window.probeResults["+JSONObject.quote(id)+"]||null");
      if(r instanceof JSONObject)return (JSONObject)r;
      SystemClock.sleep(200);
    }
    return null;
  }
  @Before public void start()throws Exception{
    scenario=ActivityScenario.launch(MainActivity.class);
    scenario.onActivity(a->{activity=a;try{web=(WebView)field("web");}catch(Exception e){throw new AssertionError(e);}});
    for(int n=0;n<100;n++){if("complete".equals(js("document.readyState")))break;SystemClock.sleep(100);}
    js("(window.probeResults={},window.nativeReply=function(r){window.probeResults[r.id]=r;},window.nativeEvent=function(){},true)");
  }
  @After public void finish(){
    if(scenario!=null)scenario.close();
  }
  @Test public void offlineModelCannotBeRequestedWithoutExplicitConsent()throws Exception{
    request("denied","downloadSpeechInputModel",new JSONObject().put("language","hi").put("offline",false).put("userInitiated",true));
    JSONObject result=response("denied",7000);
    assertNotNull(result);
    assertTrue(result.toString(),result.getString("error").contains("Offline-only"));
    ui(()->{try{
      assertEquals(false,field("listening"));
      assertEquals(0,((Map<?,?>)field("speechProbes")).size());
    }catch(Exception e){throw new AssertionError(e);}});
    System.out.println("S3_MODEL_PERMISSION_GATE_OK no microphone or provider model request");
  }
  @Test public void explicitHindiModelRequestReachesRealAndroidProviderAndReportsActualOutcome()throws Exception{
    assertTrue("Real on-device recognizer exists in this emulator",SpeechRecognizer.isOnDeviceRecognitionAvailable(activity));
    request("before","checkSpeechInput",new JSONObject().put("language","hi").put("offline",true));
    JSONObject initial=response("before",17500);
    assertNotNull("Real provider capability check returned",initial);
    assertFalse("Capability check failed "+initial,initial.has("error"));
    String before=initial.getJSONObject("value").getString("status");
    System.out.println("S3_HINDI_BEFORE_REQUEST "+initial.getJSONObject("value").toString());
    // Only when advertised as downloadable/installed; never request a new or
    // guessed model or invoke a cloud recognizer for this offline-only probe.
    if(!"download-available".equals(before) && !"installed-on-device".equals(before)){
      System.out.println("S3_HINDI_MODEL_REQUEST_SKIPPED_PROVIDER_STATUS "+before);
      return;
    }
    request("model","downloadSpeechInputModel",new JSONObject()
      .put("language","hi").put("offline",true).put("userInitiated",true));
    JSONObject outcome=response("model",30000);
    if(outcome==null){
      // The OS may present a user-consent screen or hold a scheduled download.
      // Never auto-approve it. The request is genuine but readiness unknown.
      System.out.println("S3_HINDI_MODEL_DOWNLOAD_UNCONFIRMED no callback within 30sec; no consent dialog auto-approved");
      request("cancel","cancelSpeechInputChecks",new JSONObject());
      assertNotNull(response("cancel",7500));
    }else{
      // Error, scheduled, requested, and ready are all distinct. A callback
      // does not prove that spoken Hindi was ever transcribed.
      System.out.println("S3_HINDI_MODEL_DOWNLOAD_REAL_PROVIDER_RESPONSE "+outcome.toString());
      if(!outcome.has("error")){
        String status=outcome.getJSONObject("value").optString("status","");
        assertTrue("Unexpected native status "+status,
            status.equals("ready")||status.equals("download-scheduled")
            ||status.equals("download-requested")||status.equals("download-status-unknown"));
      }
    }
    request("after","checkSpeechInput",new JSONObject().put("language","hi").put("offline",true));
    JSONObject after=response("after",17500);
    assertNotNull("Provider can be queried after preparation attempt",after);
    if(!after.has("error"))System.out.println("S3_HINDI_AFTER_REQUEST "+after.getJSONObject("value").toString());
    else System.out.println("S3_HINDI_AFTER_QUERY_ERROR "+after.getString("error"));
    ui(()->{try{assertEquals(false,field("listening"));}catch(Exception e){throw new AssertionError(e);}});
  }
}
''')
print("Generated two real-Android model preparation/consent tests, with bounded genuine provider call.")
