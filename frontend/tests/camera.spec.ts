import { test, expect } from "@playwright/test";
test.use({launchOptions:{args:["--use-fake-device-for-media-stream","--use-fake-ui-for-media-stream"]}});
test("camera capture saves a private wardrobe photo and stops the stream", async ({page}) => {
 await page.goto("/");
 await page.getByRole("button",{name:"Explore the demo wardrobe"}).click();
 await page.getByRole("button",{name:"My wardrobe"}).click();
 await page.getByRole("button",{name:"+ Add garment"}).click();
 await page.getByRole("button",{name:"Take photo"}).click();
 const video=page.locator("video");
 await expect.poll(() => video.evaluate(v => (v as HTMLVideoElement).videoWidth)).toBeGreaterThan(0);
 await video.evaluate(v => { (window as any).__cameraTestTrack=((v as HTMLVideoElement).srcObject as MediaStream).getVideoTracks()[0]; });
 await page.getByRole("button",{name:"Capture photo",exact:true}).click();
 await expect(page.getByAltText("Uploaded garment")).toBeVisible();
 expect(await page.evaluate(() => (window as any).__cameraTestTrack.readyState)).toBe("ended");
 await page.getByLabel("Garment name",{exact:true}).fill("My camera shirt");
 await page.getByRole("button",{name:"Confirm attributes & save"}).click();
 const card=page.locator("article").filter({has:page.getByRole("heading",{name:"My camera shirt",exact:true})});
 await expect(card).toBeVisible();
 await expect(card.locator("img")).toBeVisible();
 await page.reload();
 await page.getByRole("button",{name:"My wardrobe"}).click();
 await expect(page.getByRole("heading",{name:"My camera shirt",exact:true})).toBeVisible();
});
test("camera permission denial keeps photo upload available", async ({page}) => {
 await page.addInitScript(() => {
   Object.defineProperty(navigator.mediaDevices,"getUserMedia",{value:async () => {throw new DOMException("Denied","NotAllowedError");}});
 });
 await page.goto("/");
 await page.getByRole("button",{name:"Explore the demo wardrobe"}).click();
 await page.getByRole("button",{name:"My wardrobe"}).click();
 await page.getByRole("button",{name:"+ Add garment"}).click();
 await page.getByRole("button",{name:"Take photo"}).click();
 await expect(page.getByRole("alert").filter({hasText:"Camera permission was denied"})).toBeVisible();
 await page.getByRole("button",{name:"Cancel camera"}).click();
 await expect(page.getByLabel("Choose a garment photo",{exact:false})).toBeVisible();
});

test("Take photo opens native capture when live camera is unavailable", async ({page}) => {
 await page.addInitScript(() => {Object.defineProperty(navigator,"mediaDevices",{get:() => undefined});});
 await page.goto("/");
 await page.getByRole("button",{name:"Explore the demo wardrobe"}).click();
 await page.getByRole("button",{name:"My wardrobe"}).click();
 await page.getByRole("button",{name:"+ Add garment"}).click();
 const picker=page.waitForEvent("filechooser");
 await page.getByRole("button",{name:"Take photo"}).click();
 const chooser=await picker;
 await expect(page.getByLabel("Device camera photo",{exact:true})).toHaveAttribute("capture","environment");
 await chooser.setFiles("../backend/assets/photos/00.jpg");
 await expect(page.getByAltText("Uploaded garment")).toBeVisible();
 await expect(page.locator("video")).toHaveCount(0);
 await page.getByLabel("Garment name",{exact:true}).fill("Native camera shirt");
 await page.getByRole("button",{name:"Confirm attributes & save"}).click();
 await expect(page.getByRole("heading",{name:"Native camera shirt",exact:true})).toBeVisible();
});
