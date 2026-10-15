"""Generic Android download diagnostics. No private content or credentials."""
from pathlib import Path

def apply(root):
    root = Path(root)
    p = root / 'app/src/main/java/com/shift/systemsafe/MainActivity.java'
    src = p.read_text()
    anchor = ' private void translate(String id,JSONObject a,boolean prepare)'
    start = src.index(anchor)
    end = src.index(' private void finishSpeech(', start)
    replacement = r'''
 private final java.util.Map<String, com.google.android.gms.tasks.Task<Void>> modelJobs=new java.util.HashMap<>();
 private final java.util.Set<String> activeModelRequests=new java.util.HashSet<>();
 private JSONObject downloadDiagnostics(){
  JSONObject d=new JSONObject();
  try {
   android.net.ConnectivityManager cm=(android.net.ConnectivityManager)getSystemService(CONNECTIVITY_SERVICE);
   android.net.NetworkCapabilities n=cm.getNetworkCapabilities(cm.getActiveNetwork());
   d.put("networkPresent",n!=null);d.put("validated",n!=null&&n.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_VALIDATED));
   d.put("cellular",n!=null&&n.hasTransport(android.net.NetworkCapabilities.TRANSPORT_CELLULAR));
   d.put("wifi",n!=null&&n.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI));
   d.put("metered",cm.isActiveNetworkMetered());d.put("dataSaverStatus",cm.getRestrictBackgroundStatus());
   d.put("freeStorageBytes",getFilesDir().getUsableSpace());d.put("ttsReady",ttsReady);
   if(tts!=null)d.put("voiceEngine",tts.getDefaultEngine());
   JSONArray rows=new JSONArray();
   android.app.DownloadManager dm=(android.app.DownloadManager)getSystemService(DOWNLOAD_SERVICE);
   try(android.database.Cursor c=dm.query(new android.app.DownloadManager.Query())){
    if(c!=null)while(c.moveToNext()&&rows.length()<20){
     JSONObject r=new JSONObject();
     r.put("status",c.getInt(c.getColumnIndexOrThrow(android.app.DownloadManager.COLUMN_STATUS)));
     r.put("reason",c.getInt(c.getColumnIndexOrThrow(android.app.DownloadManager.COLUMN_REASON)));
     r.put("downloadedBytes",c.getLong(c.getColumnIndexOrThrow(android.app.DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR)));
     r.put("totalBytes",c.getLong(c.getColumnIndexOrThrow(android.app.DownloadManager.COLUMN_TOTAL_SIZE_BYTES)));
     rows.put(r);
    }
   }
   d.put("downloads",rows);
  }catch(Exception e){try{d.put("diagnosticError",e.getClass().getSimpleName());}catch(Exception ignored){}}
  return d;
 }
 private String safeModelError(Exception e){
  int code=e instanceof com.google.mlkit.common.MlKitException?((com.google.mlkit.common.MlKitException)e).getErrorCode():-1;
  String cause=e.getCause()==null?"none":e.getCause().getClass().getSimpleName();
  return "Language service failed (code "+code+", "+e.getClass().getSimpleName()+", cause "+cause+"). Open Language diagnostics for the device status.";
 }
 private void reportModelStatus(String id,String state,boolean mobile){
  JSONObject d=downloadDiagnostics();
  try{d.put("requestId",id);d.put("state",state);d.put("mobileAllowed",mobile);}catch(Exception ignored){}
  event("modelStatus",d);
 }
 private void completeTranslation(String id,Translator t,String text,boolean prepare){
  if(!activeModelRequests.contains(id))return;
  if(prepare){activeModelRequests.remove(id);reply(id,obj("ready",true),null);return;}
  t.translate(text).addOnSuccessListener(value->{if(activeModelRequests.remove(id))reply(id,obj("text",value),null);})
   .addOnFailureListener(e->{if(activeModelRequests.remove(id))reply(id,null,safeModelError(e));});
 }
 private void translate(String id,JSONObject a,boolean prepare){
  String from=mlLanguage(a.optString("from","en")),to=mlLanguage(a.optString("to","en"));
  if(from==null||to==null){reply(id,null,"Live translation is not supported for this language by the current on-device engine.");return;}
  String text=a.optString("text","");if(text.length()>6000){reply(id,null,"Please use a shorter passage.");return;}
  if(from.equals(to)){reply(id,prepare?obj("ready",true):obj("text",text),null);return;}
  final boolean mobile=a.optBoolean("mobileData",false);
  final Translator t=translator(from,to);final String pair=from+":"+to+":"+mobile;
  activeModelRequests.add(id);
  reportModelStatus(id,"checking",mobile);
  handler.postDelayed(()->{if(activeModelRequests.remove(id)){reportModelStatus(id,"timeout",mobile);reply(id,null,"The language service has not completed. This does not diagnose a connection fault. Open Language diagnostics to see the actual network and download status.");}},100000);
  final Runnable begin=()->{
   if(!activeModelRequests.contains(id))return;
   com.google.android.gms.tasks.Task<Void> job=modelJobs.get(pair);
   if(job==null||job.isComplete()){
    DownloadConditions.Builder conditions=new DownloadConditions.Builder();
    if(!mobile)conditions.requireWifi();
    job=mobile?t.downloadModelIfNeeded():t.downloadModelIfNeeded(conditions.build());
    modelJobs.put(pair,job);
   }
   reportModelStatus(id,"preparing",mobile);
   event("model",obj("message",mobile?"Preparing language using mobile data or Wi-Fi.":"Preparing language using Wi-Fi as selected."));
   job.addOnSuccessListener(v->completeTranslation(id,t,text,prepare))
    .addOnFailureListener(e->{if(activeModelRequests.remove(id)){reportModelStatus(id,"failed",mobile);reply(id,null,safeModelError(e));}});
  };
  com.google.mlkit.common.model.RemoteModelManager manager=com.google.mlkit.common.model.RemoteModelManager.getInstance();
  manager.getDownloadedModels(TranslateRemoteModel.class).addOnSuccessListener(models->{
   java.util.Set<String> available=new java.util.HashSet<>();for(TranslateRemoteModel m:models)available.add(m.getLanguage());
   if((from.equals("en")||available.contains(from))&&(to.equals("en")||available.contains(to))){
    reportModelStatus(id,"installed",mobile);completeTranslation(id,t,text,prepare);
   }else begin.run();
  }).addOnFailureListener(e->{if(activeModelRequests.remove(id)){reportModelStatus(id,"model-check-failed",mobile);reply(id,null,safeModelError(e));}});
 }
'''
    src = src[:start] + replacement + src[end:]
    marker = 'case "capabilities"->reply(id,capabilities(),null);'
    assert marker in src
    src = src.replace(marker, marker + '\n   case "languageDiagnostics"->reply(id,downloadDiagnostics(),null);\n   case "cancelPreparation"->{activeModelRequests.clear();reply(id,obj("cancelled",true),null);}')
    p.write_text(src)
    gradle=root/'app/build.gradle'
    g=gradle.read_text().replace('versionCode 1;', 'versionCode 2;').replace('versionName \'1.0.0\'', 'versionName \'1.0.1\'')
    gradle.write_text(g)

if __name__=='__main__':
    import sys
    apply(sys.argv[1] if len(sys.argv)>1 else 'android-shell/project')
