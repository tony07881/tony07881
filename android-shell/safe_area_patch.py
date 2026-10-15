"""Generic screen-inset fix and synthetic Android tests. No private field data."""
from pathlib import Path
import re
root=Path('android-shell/project')
p=root/'app/src/main/java/com/shift/systemsafe/MainActivity.java'
t=p.read_text()
old='web=new WebView(this); setContentView(web);'
assert t.count(old)==1
new='''getWindow().setDecorFitsSystemWindows(false);
  android.widget.FrameLayout safeRoot=new android.widget.FrameLayout(this);
  safeRoot.setTag("safe-area-root");
  safeRoot.setBackgroundColor(0xfff3f6f6);
  web=new WebView(this);
  web.setTag("field-web");
  safeRoot.addView(web,new android.widget.FrameLayout.LayoutParams(
    android.view.ViewGroup.LayoutParams.MATCH_PARENT,
    android.view.ViewGroup.LayoutParams.MATCH_PARENT));
  setContentView(safeRoot);
  // Padding belongs to the native parent, not WebView: CSS fixed controls must
  // live in a genuinely smaller viewport, above navigation and below status UI.
  safeRoot.setOnApplyWindowInsetsListener((v,insets)-> {
    android.graphics.Insets area=insets.getInsets(
      android.view.WindowInsets.Type.systemBars()
      | android.view.WindowInsets.Type.displayCutout()
      | android.view.WindowInsets.Type.ime());
    v.setPadding(area.left,area.top,area.right,area.bottom);
    return android.view.WindowInsets.CONSUMED;
  });
  safeRoot.post(safeRoot::requestApplyInsets);
  android.view.WindowInsetsController bars=getWindow().getInsetsController();
  if(bars!=null)bars.setSystemBarsAppearance(
    android.view.WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
    | android.view.WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
    android.view.WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
    | android.view.WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);'''
t=t.replace(old,new)
lines=t.splitlines()
bad=[i for i,line in enumerate(lines) if 'web.setOnApplyWindowInsetsListener' in line]
assert len(bad)==1
lines.pop(bad[0]);t='\n'.join(lines)+'\n'
old='case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED,SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE->"The phone\'s recogniser does not support this selected language, or its voice pack is missing.";'
new='''case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED->locale(listenLanguage).getDisplayLanguage(Locale.ENGLISH)+" answer recognition is not supported by the "+(preferOffline?"on-device":"selected phone")+" recogniser (code 12). Question playback uses a separate voice service.";
case SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE->locale(listenLanguage).getDisplayLanguage(Locale.ENGLISH)+" answer recognition is supported but its recognition model is currently unavailable or not downloaded (code 13). This is separate from the question voice.";'''
assert t.count(old)==1
t=t.replace(old,new)
p.write_text(t)
p=root/'app/build.gradle';g=p.read_text()
g=re.sub(r'versionCode\s+\d+;', 'versionCode 3;',g)
g=re.sub(r'versionName\s+"[^"]+"','versionName "1.0.2"',g)
g=g.replace('targetSdk 35;', 'targetSdk 35; testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner";')
g=g.replace('abiFilters "arm64-v8a"','abiFilters "arm64-v8a", "x86_64"' if __import__('os').environ.get('SYNTHETIC_EMULATOR')=='1' else 'abiFilters "arm64-v8a"')
g+='''
dependencies {
 androidTestImplementation 'androidx.test:runner:1.6.2'
 androidTestImplementation 'androidx.test.ext:junit:1.2.1'
 androidTestImplementation 'androidx.test:core:1.6.1'
 androidTestImplementation 'androidx.test.uiautomator:uiautomator:2.3.0'
}
'''
p.write_text(g)
test=r'''package com.shift.systemsafe;
import android.app.Instrumentation;
import android.graphics.Insets;
import android.graphics.Rect;
import android.view.WindowInsets;
import android.webkit.WebView;
import android.content.pm.ActivityInfo;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.uiautomator.UiDevice;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.json.JSONObject;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class SafeAreaTest {
 private static final String HTML="<!doctype html><meta name='viewport' content='width=device-width,initial-scale=1'><style>*{box-sizing:border-box}body{margin:0;font:16px sans-serif}header{position:fixed;top:0;left:0;right:0;height:64px;background:#def}main{padding:80px 16px 100px;height:1800px}nav{position:fixed;bottom:0;left:0;right:0;height:80px;display:flex;background:#ded}button{flex:1;min-width:0;min-height:56px}textarea{width:90%;height:70px}</style><header id='header'>Generic field reference</header><main><textarea id='answer'>Synthetic answer</textarea><p>No company content or speech is used.</p></main><nav id='tabs'><button onclick='window.tap=1'>Reference</button><button onclick='window.tap=2'>Audit</button><button onclick='window.tap=3'>Translate</button><button onclick='window.tap=4'>Session</button></nav>";
 private final Instrumentation instrumentation=InstrumentationRegistry.getInstrumentation();
 private WebView web;
 private MainActivity activity;
 private JSONObject js(String expression) throws Exception {
  CountDownLatch latch=new CountDownLatch(1);AtomicReference<String> value=new AtomicReference<>();
  instrumentation.runOnMainSync(()->web.evaluateJavascript(expression,v->{value.set(v);latch.countDown();}));
  assertTrue("Javascript callback",latch.await(5,TimeUnit.SECONDS));
  return new JSONObject(value.get());
 }
 private void load(ActivityScenario<MainActivity> s) throws Exception {
  s.onActivity(a->{activity=a;web=a.findViewById(android.R.id.content).findViewWithTag("field-web");web.loadDataWithBaseURL("https://appassets.androidplatform.net/assets/",HTML,"text/html","UTF-8",null);});
  for(int n=0;n<50;n++){Thread.sleep(100);try{if(js("({ready:!!document.getElementById('tabs')})").optBoolean("ready"))return;}catch(Exception ignored){}}
  fail("Synthetic page failed to load");
 }
 private void assertInside(boolean requireKeyboard) throws Exception {
  Thread.sleep(600);final int[] position=new int[4];final Rect[] bounds=new Rect[1];final Insets[] safe=new Insets[1];final boolean[] keyboard=new boolean[1];
  instrumentation.runOnMainSync(()->{int[] xy=new int[2];web.getLocationOnScreen(xy);position[0]=xy[0];position[1]=xy[1];position[2]=web.getWidth();position[3]=web.getHeight();WindowInsets i=activity.getWindow().getDecorView().getRootWindowInsets();safe[0]=i.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout()|WindowInsets.Type.ime());keyboard[0]=i.isVisible(WindowInsets.Type.ime());bounds[0]=activity.getWindowManager().getCurrentWindowMetrics().getBounds();});
  assertNotNull(safe[0]);if(requireKeyboard)assertTrue("Keyboard really visible",keyboard[0]);
  assertTrue("WebView starts after left system UI",position[0]>=bounds[0].left+safe[0].left);
  assertTrue("WebView below status/cutout",position[1]>=bounds[0].top+safe[0].top);
  assertTrue("WebView before right system UI",position[0]+position[2]<=bounds[0].right-safe[0].right);
  assertTrue("WebView above navigation/keyboard",position[1]+position[3]<=bounds[0].bottom-safe[0].bottom);
  JSONObject r=js("(()=>{let t=document.getElementById('tabs').getBoundingClientRect(),h=document.getElementById('header').getBoundingClientRect();return {top:t.top,bottom:t.bottom,left:t.left,right:t.right,headerTop:h.top,width:innerWidth,height:innerHeight};})()");
  double scale=position[2]/r.getDouble("width");
  assertTrue("CSS fixed tabs above native system bar",position[1]+r.getDouble("bottom")*scale<=bounds[0].bottom-safe[0].bottom+2);
  assertTrue("CSS fixed header visible",r.getDouble("headerTop")>=0);
  assertTrue("No horizontal tab overflow",r.getDouble("right")<=r.getDouble("width")+1&&r.getDouble("left")>=0);
  assertTrue("All four tabs fit viewport",r.getDouble("top")>=0&&r.getDouble("bottom")<=r.getDouble("height")+1);
  System.out.println("SAFE_AREA geometry="+r+" native="+java.util.Arrays.toString(position)+" insets="+safe[0]+" keyboard="+keyboard[0]);
 }
 @Test public void portraitTabsAreAboveSystemNavigationAndTappable() throws Exception {
  try(ActivityScenario<MainActivity> s=ActivityScenario.launch(MainActivity.class)){load(s);assertInside(false);
   for(int n=1;n<=4;n++){final int index=n;JSONObject r=js("(()=>{let r=document.querySelectorAll('nav button')["+(n-1)+"].getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,w:innerWidth};})()");int[] xy=new int[2];int[] width=new int[1];instrumentation.runOnMainSync(()->{web.getLocationOnScreen(xy);width[0]=web.getWidth();});double scale=width[0]/r.getDouble("w");assertTrue(UiDevice.getInstance(instrumentation).click(xy[0]+(int)(r.getDouble("x")*scale),xy[1]+(int)(r.getDouble("y")*scale)));Thread.sleep(150);assertEquals("Tab receives actual screen tap",index,js("({tap:window.tap||0})").getInt("tap"));}
  }
 }
 @Test public void landscapeReservesSideNavigation() throws Exception {
  try(ActivityScenario<MainActivity> s=ActivityScenario.launch(MainActivity.class)){load(s);s.onActivity(a->a.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE));Thread.sleep(1200);assertInside(false);s.onActivity(a->a.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT));}
 }
 @Test public void keyboardCannotCoverTabs() throws Exception {
  try(ActivityScenario<MainActivity> s=ActivityScenario.launch(MainActivity.class)){load(s);JSONObject r=js("(()=>{let r=document.getElementById('answer').getBoundingClientRect();return {x:r.x+20,y:r.y+20,w:innerWidth};})()");int[] xy=new int[2];int[] width=new int[1];instrumentation.runOnMainSync(()->{web.getLocationOnScreen(xy);width[0]=web.getWidth();});double scale=width[0]/r.getDouble("w");UiDevice.getInstance(instrumentation).click(xy[0]+(int)(r.getDouble("x")*scale),xy[1]+(int)(r.getDouble("y")*scale));Thread.sleep(1400);assertInside(true);UiDevice.getInstance(instrumentation).pressBack();Thread.sleep(500);assertInside(false);}
 }
}
'''
p=root/'app/src/androidTest/java/com/shift/systemsafe/SafeAreaTest.java';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(test)
print('Native parent-container inset fix and synthetic tests generated; version 1.0.2.')
