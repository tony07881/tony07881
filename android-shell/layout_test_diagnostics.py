"""Test-only diagnostics and screen wakeup; never used by the release application."""
from pathlib import Path
p=Path('android-shell/project/app/src/androidTest/java/com/shift/systemsafe/SafeAreaTest.java')
t=p.read_text()
marker=' private WebView web;'
extra=r'''
 @org.junit.Before public void prepareScreen() throws Exception {
  UiDevice device=UiDevice.getInstance(instrumentation);
  device.wakeUp();
  device.executeShellCommand("wm dismiss-keyguard");
  device.executeShellCommand("input keyevent KEYCODE_WAKEUP");
  device.waitForIdle();
  // A fresh hosted emulator occasionally shows a Pixel Launcher startup ANR.
  // Dismiss ONLY that explicitly identified launcher dialog. Never hide an S3 ANR.
  androidx.test.uiautomator.UiObject2 launcherDialog=device.findObject(androidx.test.uiautomator.By.textContains("Pixel Launcher isn't responding"));
  if(launcherDialog!=null){
   java.io.File dir=new java.io.File(instrumentation.getTargetContext().getExternalFilesDir(null),"layout-evidence");dir.mkdirs();
   device.takeScreenshot(new java.io.File(dir,"launcher-startup-dialog.png"));
   androidx.test.uiautomator.UiObject2 close=device.findObject(androidx.test.uiautomator.By.res("android:id/aerr_close"));
   org.junit.Assert.assertNotNull("Launcher startup dialog close control",close);
   close.click();device.waitForIdle();
   System.out.println("TEST_SETUP: closed identified Pixel Launcher startup ANR; release app unchanged.");
  }
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
t=t.replace('Thread.sleep(150);assertEquals("Tab receives actual screen tap",index,js("({tap:window.tap||0})").getInt("tap"));','Thread.sleep(650);snapshot("tab-"+index);assertEquals("Tab receives actual screen tap",index,js("({tap:window.tap||0})").getInt("tap"));')
t=t.replace('Thread.sleep(1400);assertInside(true);','Thread.sleep(2000);snapshot("keyboard");assertInside(true);')
t=t.replace('Thread.sleep(1200);assertInside(false);','Thread.sleep(1200);snapshot("landscape");assertInside(false);')
p.write_text(t)
fixture=Path('android-shell/project/app/src/debug/assets/layout_test.html')
html=fixture.read_text()+"<script>document.addEventListener('pointerdown',e=>{window.lastPointer={x:e.clientX,y:e.clientY,tag:e.target.tagName,text:e.target.innerText};},true);</script>"
fixture.write_text(html)
print('Synthetic-only debug snapshots and focus preconditions installed. Release unchanged.')
