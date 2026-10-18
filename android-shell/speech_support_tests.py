"""Generate generic Android instrumentation tests. No voice recordings or private content."""
from pathlib import Path
root=Path('android-shell/project/app/src/androidTest/java/com/shift/systemsafe')
root.mkdir(parents=True,exist_ok=True)
(root/'SpeechInputSupportTest.java').write_text(r'''package com.shift.systemsafe;
import android.content.Intent;
import android.os.SystemClock;
import android.speech.*;
import android.webkit.WebView;
import androidx.lifecycle.Lifecycle;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class SpeechInputSupportTest {
 private ActivityScenario<MainActivity> scenario;
 private MainActivity activity;
 private WebView web;
 private Method method(String name,Class<?>... types)throws Exception{Method m=MainActivity.class.getDeclaredMethod(name,types);m.setAccessible(true);return m;}
 private Object field(String name)throws Exception{Field f=MainActivity.class.getDeclaredField(name);f.setAccessible(true);return f.get(activity);}
 private void ui(Runnable action){InstrumentationRegistry.getInstrumentation().runOnMainSync(action);}
 @Before public void open()throws Exception{
  scenario=ActivityScenario.launch(MainActivity.class);
  scenario.onActivity(a->{activity=a;try{web=(WebView)field("web");}catch(Exception e){throw new AssertionError(e);}});
  for(int n=0;n<120;n++){Object v=js("document.readyState");if("complete".equals(v))break;SystemClock.sleep(100);}
  js("(window.probeResults={},window.nativeReply=function(r){window.probeResults[r.id]=r;},window.nativeEvent=function(){},true)");
 }
 @After public void close(){if(scenario!=null)scenario.close();}
 private Object js(String expression)throws Exception{
  CountDownLatch latch=new CountDownLatch(1);AtomicReference<String> value=new AtomicReference<>();
  ui(()->web.evaluateJavascript("JSON.stringify("+expression+")",v->{value.set(v);latch.countDown();}));
  assertTrue("WebView callback",latch.await(6,TimeUnit.SECONDS));
  Object outer=new JSONTokener(value.get()).nextValue();
  if(outer==JSONObject.NULL)return JSONObject.NULL;
  return new JSONTokener((String)outer).nextValue();
 }
 private void request(String id,String action,JSONObject args)throws Exception{
  js("(S3Native.request("+JSONObject.quote(id)+","+JSONObject.quote(action)+","+JSONObject.quote(args.toString())+"),true)");
 }
 private JSONObject await(String id)throws Exception{
  for(int n=0;n<170;n++){Object v=js("window.probeResults["+JSONObject.quote(id)+"]||null");if(v instanceof JSONObject)return (JSONObject)v;SystemClock.sleep(100);}
  fail("Native speech request did not finish within bounded time");return null;
 }
 @Test public void hindiLocaleAndOfflineIntentAreExact()throws Exception{
  Method locale=method("locale",String.class);Locale h=(Locale)locale.invoke(activity,"hi");assertEquals("hi-IN",h.toLanguageTag());
  Intent offline=(Intent)method("recognitionIntent",String.class,boolean.class).invoke(activity,"hi-IN",true);
  assertEquals("hi-IN",offline.getStringExtra(RecognizerIntent.EXTRA_LANGUAGE));
  assertTrue(offline.getBooleanExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE,false));
  assertEquals(RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,offline.getStringExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL));
  Intent online=(Intent)method("recognitionIntent",String.class,boolean.class).invoke(activity,"hi-IN",false);
  assertFalse(online.getBooleanExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE,true));
 }
 @Test public void languageMatchingDoesNotConfuseNeighbouringLanguages()throws Exception{
  Method m=method("languageListed",List.class,String.class);
  assertEquals(true,m.invoke(null,List.of("hi-IN"),"hi-IN"));
  assertEquals(true,m.invoke(null,List.of("hi_IN"),"hi-IN"));
  assertEquals(true,m.invoke(null,List.of("hi"),"hi-IN"));
  assertEquals(false,m.invoke(null,List.of("ur-PK","en-IN"),"hi-IN"));
  assertEquals(false,m.invoke(null,List.of("en-US"),"en-GB"));
  assertEquals(false,m.invoke(null,Collections.emptyList(),"hi-IN"));
  assertEquals(false,m.invoke(null,null,"hi-IN"));
 }
 @Test public void installedPendingDownloadableAndOnlineAreDistinct()throws Exception{
  Method m=method("speechSupportStatus",RecognitionSupport.class,String.class,boolean.class);
  assertEquals("installed-on-device",m.invoke(null,new RecognitionSupport.Builder().setInstalledOnDeviceLanguages(List.of("hi-IN")).build(),"hi-IN",true));
  assertEquals("download-pending",m.invoke(null,new RecognitionSupport.Builder().setPendingOnDeviceLanguages(List.of("hi-IN")).build(),"hi-IN",true));
  assertEquals("download-available",m.invoke(null,new RecognitionSupport.Builder().setSupportedOnDeviceLanguages(List.of("hi-IN")).build(),"hi-IN",true));
  RecognitionSupport remote=new RecognitionSupport.Builder().setOnlineLanguages(List.of("hi-IN")).build();
  assertEquals("not-offline",m.invoke(null,remote,"hi-IN",true));
  assertEquals("online-supported",m.invoke(null,remote,"hi-IN",false));
  assertEquals("not-supported-by-provider",m.invoke(null,new RecognitionSupport.Builder().setInstalledOnDeviceLanguages(List.of("en-US")).build(),"hi-IN",true));
 }
 @Test public void actualAndroidHindiCapabilityProbeNeverOpensMicrophone()throws Exception{
  request("hindi","checkSpeechInput",new JSONObject().put("language","hi").put("offline",true));
  JSONObject r=await("hindi");assertFalse(r.toString(),r.has("error"));
  JSONObject v=r.getJSONObject("value");assertEquals("hi-IN",v.getString("language"));assertTrue(v.getBoolean("offlineOnly"));
  Set<String> statuses=Set.of("installed-on-device","download-pending","download-available","not-offline","not-supported-by-provider","no-offline-service","no-service","check-timeout","check-unavailable");
  assertTrue(v.toString(),statuses.contains(v.getString("status")));
  ui(()->{try{assertEquals(false,field("listening"));assertEquals(0,((Map<?,?>)field("speechProbes")).size());}catch(Exception e){throw new AssertionError(e);}});
  System.out.println("S3_ACTUAL_ANDROID_CAPABILITY_ONLY "+v.toString());
 }
 @Test public void modelCannotDownloadWithoutExplicitUserRequest()throws Exception{
  request("unapproved","downloadSpeechInputModel",new JSONObject().put("language","hi").put("offline",true));
  JSONObject r=await("unapproved");assertTrue(r.toString(),r.getString("error").contains("explicit"));
  ui(()->{try{assertEquals(0,((Map<?,?>)field("speechProbes")).size());assertEquals(false,field("listening"));}catch(Exception e){throw new AssertionError(e);}});
 }
 @Test public void backgroundCancelsSupportProbeWithoutStartingCapture()throws Exception{
  request("background","checkSpeechInput",new JSONObject().put("language","hi").put("offline",true));
  scenario.moveToState(Lifecycle.State.CREATED);
  ui(()->{try{assertEquals(0,((Map<?,?>)field("speechProbes")).size());assertEquals(false,field("listening"));}catch(Exception e){throw new AssertionError(e);}});
 }
}
''')
print('Created 6 generic Android speech input support tests; no audio recording or model downloads.')
