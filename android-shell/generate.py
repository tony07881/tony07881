"""Build a generic Android shell. Private field-guide content is added only after download."""
from pathlib import Path
root = Path('android-shell/project')
files = {}
files['settings.gradle'] = "pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\ndependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\nrootProject.name='FieldCompanion'\ninclude ':app'\n"
files['build.gradle'] = "plugins { id 'com.android.application' version '8.7.3' apply false }\n"
files['gradle.properties'] = 'android.useAndroidX=true\norg.gradle.jvmargs=-Xmx3g\n'
files['app/build.gradle'] = """plugins { id 'com.android.application' }
android {
 namespace 'com.shift.systemsafe'; compileSdk 35
 defaultConfig { applicationId 'com.shift.systemsafe'; minSdk 26; targetSdk 35; versionCode 1; versionName '1.0.0' }
 compileOptions { sourceCompatibility JavaVersion.VERSION_17; targetCompatibility JavaVersion.VERSION_17 }
 buildTypes { release { minifyEnabled false } }
}
dependencies {
 implementation 'androidx.webkit:webkit:1.12.1'
 implementation 'androidx.core:core:1.15.0'
 implementation 'com.google.mlkit:translate:17.0.3'
}
"""
files['app/src/main/AndroidManifest.xml'] = '''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
 <uses-permission android:name="android.permission.INTERNET"/>
 <uses-permission android:name="android.permission.RECORD_AUDIO"/>
 <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
 <queries><intent><action android:name="android.intent.action.TTS_SERVICE"/></intent><intent><action android:name="android.speech.RecognitionService"/></intent></queries>
 <application android:label="S3" android:icon="@drawable/app_icon" android:allowBackup="false" android:usesCleartextTraffic="false" android:theme="@android:style/Theme.Material.Light.NoActionBar">
  <activity android:name=".MainActivity" android:exported="true" android:configChanges="orientation|screenSize|keyboardHidden" android:windowSoftInputMode="adjustResize"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity>
  <provider android:name="androidx.core.content.FileProvider" android:authorities="com.shift.systemsafe.files" android:exported="false" android:grantUriPermissions="true"><meta-data android:name="android.support.FILE_PROVIDER_PATHS" android:resource="@xml/file_paths"/></provider>
 </application>
</manifest>'''
files['app/src/main/res/xml/file_paths.xml'] = '<paths><cache-path name="shared" path="shared/"/></paths>'
files['app/src/main/res/drawable/app_icon.xml'] = '''<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108"><path android:fillColor="#075E61" android:pathData="M0,0h108v108h-108z"/><path android:fillColor="#FFFFFF" android:pathData="M21,28h30v10h-20v11h20v30h-30v-10h20v-10h-20z M59,28h27v51h-27v-10h17v-11h-14v-10h14v-10h-17z"/></vector>'''
files['app/src/main/assets/index.html'] = '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Field companion shell</title><h1>Build shell</h1><p>No private field-guide content is included in this public build.</p>'
files['app/src/main/java/com/shift/systemsafe/MainActivity.java'] = r'''package com.shift.systemsafe;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.AudioAttributes;
import android.media.AudioDeviceInfo;
import android.media.AudioManager;
import android.net.Uri;
import android.os.*;
import android.speech.*;
import android.speech.tts.*;
import android.webkit.*;
import android.view.View;
import androidx.webkit.WebViewAssetLoader;
import androidx.core.content.FileProvider;
import com.google.mlkit.common.model.DownloadConditions;
import com.google.mlkit.nl.translate.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class MainActivity extends Activity {
 private WebView web;
 private TextToSpeech tts;
 private boolean ttsReady=false;
 private SpeechRecognizer recognizer;
 private final Handler handler=new Handler(Looper.getMainLooper());
 private final Map<String,Translator> translators=new HashMap<>();
 private final Map<String,String> speechRequests=new HashMap<>();
 private boolean listening=false, live=false, preferOffline=true;
 private String listenLanguage="en-GB", pendingMicId=null, exportId=null;
 private JSONObject pendingMicArgs=null;
 private byte[] exportBytes;
 private int generation=0, retryCount=0;
 private long startedAt;
 private final String origin="https://appassets.androidplatform.net";

 @Override public void onCreate(Bundle state) {
  super.onCreate(state);
  web=new WebView(this); setContentView(web);
  web.setBackgroundColor(0xfff4f7f7);
  web.getSettings().setJavaScriptEnabled(true);
  web.getSettings().setDomStorageEnabled(true);
  web.getSettings().setAllowFileAccess(false);
  web.getSettings().setAllowContentAccess(false);
  web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
  web.getSettings().setMediaPlaybackRequiresUserGesture(true);
  web.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
  web.setOnApplyWindowInsetsListener((v,insets)-> { if(Build.VERSION.SDK_INT>=30) { android.graphics.Insets b=insets.getInsets(android.view.WindowInsets.Type.systemBars() | android.view.WindowInsets.Type.ime()); v.setPadding(b.left,b.top,b.right,b.bottom); } return insets; });
  WebViewAssetLoader loader=new WebViewAssetLoader.Builder().addPathHandler("/assets/",new WebViewAssetLoader.AssetsPathHandler(this)).build();
  web.setWebViewClient(new WebViewClient(){
   @Override public WebResourceResponse shouldInterceptRequest(WebView v,WebResourceRequest r) { if(!"appassets.androidplatform.net".equals(r.getUrl().getHost())) return new WebResourceResponse("text/plain","UTF-8",403,"Blocked",Collections.emptyMap(),new ByteArrayInputStream(new byte[0])); return loader.shouldInterceptRequest(r.getUrl()); }
   @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r) { return !r.getUrl().toString().startsWith(origin+"/assets/"); }
  });
  web.addJavascriptInterface(new Bridge(),"S3Native");
  tts=new TextToSpeech(this,status->{ ttsReady=status==TextToSpeech.SUCCESS; if(ttsReady) { tts.setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()); tts.setOnUtteranceProgressListener(new UtteranceProgressListener(){
   public void onStart(String id){event("speechStart",obj("id",id));}
   public void onDone(String id){handler.post(()->finishSpeech(id,null));}
   public void onError(String id){handler.post(()->finishSpeech(id,"The phone could not speak this text."));}
   public void onStop(String id,boolean interrupted){handler.post(()->finishSpeech(id,"Speech stopped."));}
  }); } event("ready",obj("speech",ttsReady)); });
  web.loadUrl(origin+"/assets/index.html");
 }
 private JSONObject obj(String key,Object value) { JSONObject o=new JSONObject(); try{o.put(key,value);}catch(Exception ignored){} return o; }
 private void reply(String id,Object value,String error) { JSONObject o=new JSONObject(); try{o.put("id",id);o.put("value",value);if(error!=null)o.put("error",error);}catch(Exception ignored){} final String script="window.nativeReply&&window.nativeReply("+o+")";handler.post(()->{if(web!=null)web.evaluateJavascript(script,null);}); }
 private void event(String type,JSONObject value) { JSONObject o=obj("type",type);try{o.put("data",value);}catch(Exception ignored){} final String script="window.nativeEvent&&window.nativeEvent("+o+")";handler.post(()->{if(web!=null)web.evaluateJavascript(script,null);}); }
 private String readAsset(String name) throws IOException { try(InputStream in=getAssets().open(name);ByteArrayOutputStream out=new ByteArrayOutputStream()){in.transferTo(out);return out.toString(StandardCharsets.UTF_8);} }
 private String mlLanguage(String code){String b=code.split("-")[0];if(b.equals("fil"))b="tl";return TranslateLanguage.getAllLanguages().contains(b)?b:null;}
 private Locale locale(String code){Map<String,String> m=Map.of("en","en-GB","ar","ar-QA","hi","hi-IN","ur","ur-PK","ne","ne-NP","bn","bn-BD","ml","ml-IN","si","si-LK","ta","ta-IN","tl","fil-PH");return Locale.forLanguageTag(m.getOrDefault(code,code));}
 private boolean headphones() {AudioManager am=(AudioManager)getSystemService(AUDIO_SERVICE);for(AudioDeviceInfo d:am.getDevices(AudioManager.GET_DEVICES_OUTPUTS)){int t=d.getType();if(t==AudioDeviceInfo.TYPE_BLUETOOTH_A2DP||t==AudioDeviceInfo.TYPE_WIRED_HEADPHONES||t==AudioDeviceInfo.TYPE_WIRED_HEADSET||t==AudioDeviceInfo.TYPE_USB_HEADSET||t==AudioDeviceInfo.TYPE_HEARING_AID||t==AudioDeviceInfo.TYPE_BLE_HEADSET)return true;}return false;}
 private JSONObject capabilities() throws Exception {JSONObject r=new JSONObject();r.put("ttsReady",ttsReady);r.put("recognition",SpeechRecognizer.isRecognitionAvailable(this));r.put("onDeviceRecognition",Build.VERSION.SDK_INT>=31&&SpeechRecognizer.isOnDeviceRecognitionAvailable(this));r.put("headphones",headphones());JSONArray langs=new JSONArray();for(String c:new String[]{"en","ar","hi","ur","ne","bn","ml","si","ta","tl"}){JSONObject x=obj("code",c);x.put("translation",c.equals("en")||mlLanguage(c)!=null);x.put("voice",ttsReady&&tts.isLanguageAvailable(locale(c))>=TextToSpeech.LANG_AVAILABLE);langs.put(x);}r.put("languages",langs);return r;}
 private Translator translator(String from,String to){String k=from+":"+to;Translator t=translators.get(k);if(t==null){t=Translation.getClient(new TranslatorOptions.Builder().setSourceLanguage(from).setTargetLanguage(to).build());translators.put(k,t);}return t;}
 private void translate(String id,JSONObject a,boolean prepare){String from=mlLanguage(a.optString("from","en")),to=mlLanguage(a.optString("to","en"));if(from==null||to==null){reply(id,null,"This language is not supported by the installed offline translation engine. No text was sent to an online service.");return;}String text=a.optString("text","");if(text.length()>6000){reply(id,null,"Please use a shorter passage.");return;}if(from.equals(to)){reply(id,prepare?obj("ready",true):obj("text",text),null);return;}Translator t=translator(from,to);DownloadConditions.Builder b=new DownloadConditions.Builder();if(!a.optBoolean("mobileData",false))b.requireWifi();event("model",obj("message","Preparing translation model. Connect to Wi-Fi for the first download."));t.downloadModelIfNeeded(b.build()).addOnSuccessListener(v->{if(prepare){reply(id,obj("ready",true),null);return;}t.translate(text).addOnSuccessListener(s->reply(id,obj("text",s),null)).addOnFailureListener(e->reply(id,null,"Translation failed. Try again."));}).addOnFailureListener(e->reply(id,null,"The translation model is not ready. Connect to Wi-Fi and try Prepare language."));}
 private void finishSpeech(String id,String error){String request=speechRequests.remove(id);if(request!=null)reply(request,obj("finished",error==null),error);event("speechEnd",obj("id",id));}
 private void speak(String id,JSONObject a){if(!ttsReady){reply(id,null,"Phone speech is still loading. Try again in a moment.");return;}Locale l=locale(a.optString("language","en"));if(tts.isLanguageAvailable(l)<TextToSpeech.LANG_AVAILABLE){reply(id,null,"This voice is not installed. Open Voice settings to install it.");return;}String text=a.optString("text","");if(text.isBlank()){reply(id,null,"There is no text to speak.");return;}if(text.length()>TextToSpeech.getMaxSpeechInputLength()){reply(id,null,"Text is too long to speak in one phrase.");return;}tts.setLanguage(l);tts.setSpeechRate((float)Math.min(1.15,Math.max(.65,a.optDouble("rate",.9))));String utterance=UUID.randomUUID().toString();speechRequests.put(utterance,id);int result=tts.speak(text,TextToSpeech.QUEUE_ADD,new Bundle(),utterance);if(result==TextToSpeech.ERROR)finishSpeech(utterance,"Speech could not start.");}
 private void stopSpeech(){if(tts!=null)tts.stop();for(String k:new ArrayList<>(speechRequests.keySet()))finishSpeech(k,"Speech stopped.");}
 private void stopListening(){listening=false;generation++;if(recognizer!=null){recognizer.cancel();recognizer.destroy();recognizer=null;}event("listening",obj("active",false));}
 private void startListening(String id,JSONObject a){if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){pendingMicId=id;pendingMicArgs=a;requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},101);return;}stopListening();live=a.optBoolean("live",false);preferOffline=a.optBoolean("offline",true);listenLanguage=locale(a.optString("language","en")).toLanguageTag();if(!SpeechRecognizer.isRecognitionAvailable(this)){reply(id,null,"No speech recognition service is installed on this phone.");return;}boolean local=Build.VERSION.SDK_INT>=31&&SpeechRecognizer.isOnDeviceRecognitionAvailable(this);if(preferOffline&&!local){reply(id,null,"On-device speech recognition is unavailable. In Audio settings you may explicitly allow the phone's online speech service.");return;}recognizer=preferOffline?SpeechRecognizer.createOnDeviceSpeechRecognizer(this):SpeechRecognizer.createSpeechRecognizer(this);listening=true;retryCount=0;startedAt=android.os.SystemClock.elapsedRealtime();final int ticket=++generation;recognizer.setRecognitionListener(new RecognitionListener(){
 public void onReadyForSpeech(Bundle p){if(ticket==generation)event("listening",obj("active",true));}
 public void onBeginningOfSpeech(){} public void onRmsChanged(float f){} public void onBufferReceived(byte[] b){} public void onEndOfSpeech(){} public void onEvent(int t,Bundle p){}
 public void onPartialResults(Bundle b){if(ticket!=generation)return;ArrayList<String> v=b.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);if(v!=null&&!v.isEmpty())event("partial",obj("text",v.get(0)));}
 public void onResults(Bundle b){if(ticket!=generation)return;retryCount=0;ArrayList<String> v=b.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);if(v!=null&&!v.isEmpty()){JSONObject r=obj("text",v.get(0));try{float[] scores=b.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES);r.put("confidence",scores!=null&&scores.length>0?scores[0]:-1);}catch(Exception ignored){}event("result",r);}if(live)scheduleNext(ticket,400);else stopListening();}
 public void onError(int code){if(ticket!=generation)return;boolean transientError=code==SpeechRecognizer.ERROR_NO_MATCH||code==SpeechRecognizer.ERROR_SPEECH_TIMEOUT||code==SpeechRecognizer.ERROR_RECOGNIZER_BUSY;if(live&&transientError&&++retryCount<=5){scheduleNext(ticket,1000);return;}String message=switch(code){case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED,SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE->"The phone's recogniser does not support this selected language, or its voice pack is missing.";case SpeechRecognizer.ERROR_NETWORK,SpeechRecognizer.ERROR_NETWORK_TIMEOUT->"Speech recognition has no network connection.";case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS->"Microphone permission was not granted.";case SpeechRecognizer.ERROR_NO_MATCH,SpeechRecognizer.ERROR_SPEECH_TIMEOUT->"No clear speech was heard. Please repeat.";default->"Speech recognition stopped ("+code+"). Please retry.";};event("recognitionError",obj("message",message));stopListening();}
 });beginRecognition(ticket);reply(id,obj("started",true),null);handler.postDelayed(()->{if(ticket==generation){event("recognitionError",obj("message",live?"Five-minute session limit reached. Start a new session.":"Recording time limit reached."));stopListening();}},live?300000:60000);}
 private void scheduleNext(int ticket,int delay){handler.postDelayed(()->{if(listening&&ticket==generation)beginRecognition(ticket);},delay);}
 private void beginRecognition(int ticket){if(!listening||ticket!=generation||recognizer==null)return;Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,listenLanguage);i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,true);i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,1);i.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE,preferOffline);try{recognizer.startListening(i);}catch(Exception e){event("recognitionError",obj("message","Unable to start the phone microphone."));stopListening();}}
 private void pdf(String id){try{File dir=new File(getCacheDir(),"shared");dir.mkdirs();File f=new File(dir,"Field_Reference.pdf");try(InputStream in=getAssets().open("booklet.pdf");OutputStream out=new FileOutputStream(f)){in.transferTo(out);}Uri uri=FileProvider.getUriForFile(this,"com.shift.systemsafe.files",f);Intent intent=new Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/pdf").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(intent);reply(id,obj("opened",true),null);}catch(Exception e){reply(id,null,"No PDF viewer is available. The complete reference is also inside this app.");}}
 private class Bridge {
  @JavascriptInterface public void request(String id,String method,String raw){handler.post(()->{try{JSONObject a=new JSONObject(raw);switch(method){
   case "content"->reply(id,new JSONObject(readAsset("content.json")),null);
   case "capabilities"->reply(id,capabilities(),null);
   case "translate"->translate(id,a,false);
   case "prepare"->translate(id,a,true);
   case "speak"->speak(id,a);
   case "stopSpeech"->{stopSpeech();reply(id,obj("stopped",true),null);}
   case "listen"->startListening(id,a);
   case "stopListening"->{stopListening();reply(id,obj("stopped",true),null);}
   case "finishListening"->{if(recognizer!=null){live=false;recognizer.stopListening();}reply(id,obj("finishing",true),null);}
   case "voiceSettings"->{startActivity(new Intent("com.android.settings.TTS_SETTINGS"));reply(id,obj("opened",true),null);}
   case "pdf"->pdf(id);
   case "export"->{if(exportId!=null){reply(id,null,"Finish the current export first.");return;}exportId=id;exportBytes=a.optString("text","").getBytes(StandardCharsets.UTF_8);Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("text/csv").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"S3_Audit.csv");startActivityForResult(i,102);}
   default->reply(id,null,"Unknown device action.");
  }}catch(Exception e){reply(id,null,"The device action could not be completed.");}});}
 }
 @Override public void onRequestPermissionsResult(int r,String[] p,int[] g){super.onRequestPermissionsResult(r,p,g);if(r==101){String id=pendingMicId;JSONObject a=pendingMicArgs;pendingMicId=null;pendingMicArgs=null;if(id!=null){if(g.length>0&&g[0]==PackageManager.PERMISSION_GRANTED)startListening(id,a);else reply(id,null,"Microphone permission was declined.");}}}
 @Override protected void onActivityResult(int r,int result,Intent data){super.onActivityResult(r,result,data);if(r==102&&exportId!=null){String id=exportId;exportId=null;try{if(result==RESULT_OK&&data!=null&&data.getData()!=null){try(OutputStream out=getContentResolver().openOutputStream(data.getData())){out.write(exportBytes);}reply(id,obj("saved",true),null);}else reply(id,null,"Export cancelled.");}catch(Exception e){reply(id,null,"The export could not be saved.");}exportBytes=null;}}
 @Override protected void onPause(){stopListening();stopSpeech();event("paused",obj("reason","App left the foreground."));super.onPause();}
 @Override protected void onDestroy(){stopListening();stopSpeech();if(tts!=null)tts.shutdown();for(Translator t:translators.values())t.close();translators.clear();if(web!=null){web.removeJavascriptInterface("S3Native");web.destroy();web=null;}super.onDestroy();}
 @Override public void onBackPressed(){if(web!=null)web.evaluateJavascript("window.appBack&&window.appBack()",null);else super.onBackPressed();}
}
'''
for name, content in files.items():
 p=root/name
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(content)
print(f'Created {len(files)} generic Android project files; no private booklet content.')
