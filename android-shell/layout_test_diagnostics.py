"""Test-only diagnostics, launcher setup and stable screen taps. No release modifications."""
from pathlib import Path
import re
p=Path('android-shell/project/app/src/androidTest/java/com/shift/systemsafe/SafeAreaTest.java')
t=p.read_text()
marker=' private WebView web;'
extra=r'''
 @org.junit.Before public void prepareScreen() throws Exception {
  UiDevice device=UiDevice.getInstance(instrumentation);
  device.wakeUp();device.executeShellCommand("wm dismiss-keyguard");device.executeShellCommand("input keyevent KEYCODE_WAKEUP");device.waitForIdle();
  androidx.test.uiautomator.UiObject2 launcherDialog=device.findObject(androidx.test.uiautomator.By.textContains("Pixel Launcher isn't responding"));
  if(launcherDialog!=null){
   java.io.File dir=new java.io.File(instrumentation.getTargetContext().getExternalFilesDir(null),"layout-evidence");dir.mkdirs();
   device.takeScreenshot(new java.io.File(dir,"launcher-startup-dialog.png"));
   androidx.test.uiautomator.UiObject2 close=device.findObject(androidx.test.uiautomator.By.res("android:id/aerr_close"));
   org.junit.Assert.assertNotNull("Launcher startup dialog close control",close);close.click();device.waitForIdle();
   System.out.println("TEST_SETUP: closed identified Pixel Launcher startup ANR; release app unchanged.");
  }
 }
 private int[] nativeRect(){int[] p=new int[5];instrumentation.runOnMainSync(()->{int[] xy=new int[2];web.getLocationOnScreen(xy);p[0]=xy[0];p[1]=xy[1];p[2]=web.getWidth();p[3]=web.getHeight();p[4]=activity.hasWindowFocus()?1:0;});return p;}
 private int[] stableWindow() throws Exception {
  int[] previous=null;int stable=0;
  for(int n=0;n<150;n++){int[] now=nativeRect();if(now[4]==1&&java.util.Arrays.equals(now,previous))stable++;else stable=0;if(stable>=10)return now;previous=now;Thread.sleep(100);}
  fail("Emulator window did not settle with app focus");return null;
 }
 private void tapStableTab(int index) throws Exception {
  for(int attempt=0;attempt<2;attempt++){
   int[] before=stableWindow();assertInside(false);
   JSONObject r=js("(()=>{let r=document.querySelectorAll('nav button')["+(index-1)+"].getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,w:innerWidth};})()");
   before=nativeRect();double scale=before[2]/r.getDouble("w");
   assertTrue("Actual screen input injected",UiDevice.getInstance(instrumentation).click(before[0]+(int)(r.getDouble("x")*scale),before[1]+(int)(r.getDouble("y")*scale)));
   int seen=0;
   for(int wait=0;wait<30;wait++){Thread.sleep(100);seen=js("({tap:window.tap||0})").getInt("tap");if(seen==index){snapshot("tab-"+index);assertInside(false);return;}}
   int[] after=nativeRect();snapshot("tab-"+index+"-attempt-"+attempt);
   if(java.util.Arrays.equals(before,after))assertEquals("Tab receives actual screen tap at stable bounds",index,seen);
   System.out.println("TEST_SETUP: window changed during pointer input; remeasure once: "+java.util.Arrays.toString(before)+" -> "+java.util.Arrays.toString(after));
  }
  assertEquals("Tab receives actual screen tap after layout settles",index,js("({tap:window.tap||0})").getInt("tap"));
 }
 private void snapshot(String name) {
  try {
   java.io.File dir=new java.io.File(instrumentation.getTargetContext().getExternalFilesDir(null),"layout-evidence");dir.mkdirs();
   UiDevice.getInstance(instrumentation).takeScreenshot(new java.io.File(dir,name+".png"));
   UiDevice.getInstance(instrumentation).dumpWindowHierarchy(new java.io.File(dir,name+".xml"));
   instrumentation.runOnMainSync(()->System.out.println("LAYOUT_FOCUS activity="+activity.hasWindowFocus()+" webFocus="+web.hasWindowFocus()+" width="+web.getWidth()+" height="+web.getHeight()+" scale="+web.getScale()+" density="+web.getResources().getDisplayMetrics().density));
   System.out.println("LAYOUT_DOM "+name+" "+js("({url:location.href,click:window.tap||0,pointer:window.lastPointer||null,focused:document.hasFocus(),active:document.activeElement?document.activeElement.tagName:null,scale:visualViewport.scale,offset:visualViewport.offsetTop})"));
  } catch(Exception e){System.out.println("LAYOUT_CAPTURE_ERROR "+e.getClass().getSimpleName());}
 }
'''
assert marker in t
t=t.replace(marker,extra+marker)
t,n=re.subn(r'for\(int n=1;n<=4;n\+\+\)\{final int index=n;[^\n]+', 'for(int n=1;n<=4;n++){tapStableTab(n);}',t)
assert n==1,'Expected exact old physical-tap loop'
t=t.replace('Thread.sleep(1400);assertInside(true);','Thread.sleep(2000);snapshot("keyboard");assertInside(true);')
t=t.replace('Thread.sleep(1200);assertInside(false);','Thread.sleep(1200);snapshot("landscape");assertInside(false);')
p.write_text(t)
fixture=Path('android-shell/project/app/src/debug/assets/layout_test.html')
html=fixture.read_text()+"<script>document.addEventListener('pointerdown',e=>{window.lastPointer={x:e.clientX,y:e.clientY,tag:e.target.tagName,text:e.target.innerText};},true);</script>"
fixture.write_text(html)
print('Synthetic-only diagnostics, stable native geometry and real tap assertions installed. Release unchanged.')
