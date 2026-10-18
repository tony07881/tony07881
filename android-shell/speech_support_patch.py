"""Generic Android speech-input support and explicit on-device preparation.
No company content, recordings, credentials or external endpoints.
Apply after generate.py, mobile_language_patch.py and safe_area_patch.py.
"""
from pathlib import Path
import re

insert = r'''
 private final java.util.Map<String,SpeechRecognizer> speechProbes=new java.util.HashMap<>();
 private void closeSpeechProbe(String id){SpeechRecognizer r=speechProbes.remove(id);if(r!=null)r.destroy();}
 private void cancelSpeechInputChecks(){
  for(String id:new java.util.ArrayList<>(speechProbes.keySet())){closeSpeechProbe(id);reply(id,null,"Speech preparation stopped. Nothing was recorded.");}
 }
 private Intent recognitionIntent(String tag,boolean offline){
  Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
  i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
  i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,tag);
  i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,true);
  i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,1);
  i.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE,offline);
  return i;
 }
 private SpeechRecognizer speechChecker(boolean offline){
  if(!offline&&!SpeechRecognizer.isRecognitionAvailable(this))throw new IllegalStateException("No recognition service installed");
  if(offline&&!SpeechRecognizer.isOnDeviceRecognitionAvailable(this))throw new IllegalStateException("No on-device recognition service installed");
  return offline?SpeechRecognizer.createOnDeviceSpeechRecognizer(this):SpeechRecognizer.createSpeechRecognizer(this);
 }
 private static boolean languageListed(java.util.List<String> languages,String tag){
  if(languages==null||tag==null||tag.isEmpty())return false;
  java.util.Locale wanted=java.util.Locale.forLanguageTag(tag);
  for(String code:languages){
   if(code==null||code.isEmpty())continue;
   java.util.Locale item=java.util.Locale.forLanguageTag(code.replace('_','-'));
   if(item.getLanguage().equals(wanted.getLanguage())&&(item.getCountry().isEmpty()||wanted.getCountry().isEmpty()||item.getCountry().equals(wanted.getCountry())))return true;
  }
  return false;
 }
 private static String speechSupportStatus(RecognitionSupport info,String tag,boolean offline){
  if(languageListed(info.getInstalledOnDeviceLanguages(),tag))return "installed-on-device";
  if(languageListed(info.getPendingOnDeviceLanguages(),tag))return "download-pending";
  if(languageListed(info.getSupportedOnDeviceLanguages(),tag))return "download-available";
  if(languageListed(info.getOnlineLanguages(),tag))return offline?"not-offline":"online-supported";
  return "not-supported-by-provider";
 }
 private void checkSpeechInput(String id,JSONObject a){
  String tag=locale(a.optString("language","en")).toLanguageTag();
  boolean offline=a.optBoolean("offline",true);
  JSONObject result=obj("language",tag);
  try{result.put("offlineOnly",offline);result.put("serviceAvailable",SpeechRecognizer.isRecognitionAvailable(this));result.put("offlineServiceAvailable",SpeechRecognizer.isOnDeviceRecognitionAvailable(this));}catch(Exception ignored){}
  if(offline&&!SpeechRecognizer.isOnDeviceRecognitionAvailable(this)){
   try{result.put("status","no-offline-service");result.put("message","This phone has no on-device speech recognition service.");}catch(Exception ignored){}
   reply(id,result,null);return;
  }
  if(!offline&&!SpeechRecognizer.isRecognitionAvailable(this)){
   try{result.put("status","no-service");}catch(Exception ignored){}
   reply(id,result,null);return;
  }
  final SpeechRecognizer probe;
  try{probe=speechChecker(offline);}catch(Exception e){reply(id,null,"Speech recognition service cannot be opened: "+e.getClass().getSimpleName());return;}
  speechProbes.put(id,probe);
  final java.util.concurrent.atomic.AtomicBoolean finished=new java.util.concurrent.atomic.AtomicBoolean(false);
  final Runnable close=()->{if(finished.compareAndSet(false,true))closeSpeechProbe(id);};
  handler.postDelayed(()->{if(speechProbes.containsKey(id)&&finished.compareAndSet(false,true)){
   closeSpeechProbe(id);try{result.put("status","check-timeout");result.put("message","The phone's recogniser did not respond to the support check.");}catch(Exception ignored){}
   reply(id,result,null);
  }},12000);
  try{probe.checkRecognitionSupport(recognitionIntent(tag,offline),getMainExecutor(),new RecognitionSupportCallback(){
   @Override public void onSupportResult(RecognitionSupport info){
    if(finished.get()||!speechProbes.containsKey(id))return;
    try{
     result.put("installedOnDevice",new JSONArray(info.getInstalledOnDeviceLanguages()));
     result.put("availableToDownload",new JSONArray(info.getSupportedOnDeviceLanguages()));
     result.put("downloadPending",new JSONArray(info.getPendingOnDeviceLanguages()));
     result.put("onlineLanguages",new JSONArray(info.getOnlineLanguages()));
     result.put("status",speechSupportStatus(info,tag,offline));
    }catch(Exception ignored){}
    close.run();reply(id,result,null);
   }
   @Override public void onError(int code){
    if(finished.get()||!speechProbes.containsKey(id))return;
    try{result.put("status","check-unavailable");result.put("errorCode",code);result.put("message",code==SpeechRecognizer.ERROR_CANNOT_CHECK_SUPPORT?"This speech provider does not report language support.":"The speech provider could not report language support (code "+code+").");}catch(Exception ignored){}
    close.run();reply(id,result,null);
   }
  });}catch(Exception e){close.run();reply(id,null,"Speech compatibility check failed: "+e.getClass().getSimpleName());}
 }
 private void downloadSpeechInputModel(String id,JSONObject a){
  String tag=locale(a.optString("language","en")).toLanguageTag();
  if(!a.optBoolean("userInitiated",false)){reply(id,null,"Use the explicit Prepare speech input button before requesting a model.");return;}
  if(!a.optBoolean("offline",true)){reply(id,null,"Offline-only must be enabled before preparing an on-device speech model.");return;}
  if(!SpeechRecognizer.isOnDeviceRecognitionAvailable(this)){reply(id,null,"The phone does not offer an on-device recognition service.");return;}
  final SpeechRecognizer probe;
  try{probe=speechChecker(true);}catch(Exception e){reply(id,null,"Speech recogniser could not open.");return;}
  speechProbes.put(id,probe);
  final Intent request=recognitionIntent(tag,true);
  if(Build.VERSION.SDK_INT>=34){
   final java.util.concurrent.atomic.AtomicBoolean done=new java.util.concurrent.atomic.AtomicBoolean(false);
   handler.postDelayed(()->{if(speechProbes.containsKey(id)&&done.compareAndSet(false,true)){closeSpeechProbe(id);reply(id,obj("status","download-status-unknown"),null);}},120000);
   try{probe.triggerModelDownload(request,getMainExecutor(),new ModelDownloadListener(){
    @Override public void onProgress(int completedPercent){if(speechProbes.containsKey(id)&&!done.get())event("speechModelProgress",obj("percent",completedPercent));}
    @Override public void onSuccess(){if(speechProbes.containsKey(id)&&done.compareAndSet(false,true)){closeSpeechProbe(id);reply(id,obj("status","ready"),null);}}
    @Override public void onScheduled(){if(speechProbes.containsKey(id)&&done.compareAndSet(false,true)){closeSpeechProbe(id);reply(id,obj("status","download-scheduled"),null);}}
    @Override public void onError(int error){if(speechProbes.containsKey(id)&&done.compareAndSet(false,true)){closeSpeechProbe(id);reply(id,null,"Android could not prepare the language pack (code "+error+").");}}
   });}catch(Exception e){done.set(true);closeSpeechProbe(id);reply(id,null,"Speech model request failed: "+e.getClass().getSimpleName());}
  }else{
   try{probe.triggerModelDownload(request);reply(id,obj("status","download-requested"),null);}
   catch(Exception e){reply(id,null,"Android declined the language-pack request.");}
   finally{closeSpeechProbe(id);}
  }
 }
'''

def apply(root):
    root=Path(root)
    p=root/'app/src/main/java/com/shift/systemsafe/MainActivity.java'
    s=p.read_text()
    assert 'private void checkSpeechInput(' not in s, 'Patch already applied'
    anchor=' private void startListening(String id,JSONObject a)'
    assert s.count(anchor)==1,'Unexpected original recognizer layout'
    s=s.replace(anchor,insert+'\n'+anchor)
    old='case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED,SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE->"The phone\'s recogniser does not support this selected language, or its voice pack is missing.";'
    new='case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED->"The phone recogniser cannot understand "+listenLanguage+" with this recognition service. Use Check speech input for an exact report.";case SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE->"The "+listenLanguage+" recognition model may not be downloaded. Use Check speech input to see if an on-device language pack is available.";'
    if s.count(old)==1:s=s.replace(old,new)
    else:
        earlier='case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED->locale(listenLanguage).getDisplayLanguage(Locale.ENGLISH)+" answer recognition is not supported by the "+(preferOffline?"on-device":"selected phone")+" recogniser (code 12). Question playback uses a separate voice service.";\ncase SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE->locale(listenLanguage).getDisplayLanguage(Locale.ENGLISH)+" answer recognition is supported but its recognition model is currently unavailable or not downloaded (code 13). This is separate from the question voice.";'
        assert s.count(earlier)==1,'Unknown recognition error layout'
        s=s.replace(earlier,new)
    marker='case "listen"->startListening(id,a);'
    assert s.count(marker)==1
    s=s.replace(marker,marker+'\n   case "checkSpeechInput"->checkSpeechInput(id,a);\n   case "downloadSpeechInputModel"->downloadSpeechInputModel(id,a);\n   case "cancelSpeechInputChecks"->{cancelSpeechInputChecks();reply(id,obj("cancelled",true),null);}')
    s=s.replace('protected void onPause(){','protected void onPause(){cancelSpeechInputChecks();',1)
    s=s.replace('protected void onDestroy(){','protected void onDestroy(){cancelSpeechInputChecks();',1)
    p.write_text(s)
    g=root/'app/build.gradle'
    t=g.read_text()
    t=re.sub(r'versionCode \d+;', 'versionCode 4;',t)
    t=re.sub(r"versionName '[^']+'", "versionName '1.0.3'",t)
    g.write_text(t)
    print('Applied generic speech support/preparation, version 1.0.3; no microphone or model started.')

if __name__=='__main__':
 import sys
 apply(sys.argv[1] if len(sys.argv)>1 else 'android-shell/project')
