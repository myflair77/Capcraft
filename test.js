const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    
    await page.goto('file:///' + path.resolve('index.html').replace(/\\/g, '/'));
    await page.setViewport({ width: 1200, height: 800 });

    // Click 'rect' button
    await page.click('#btn_rect');
    
    // Click canvas to draw
    const canvas = await page.$('#mainCanvas');
    const box = await canvas.boundingBox();
    await page.mouse.click(box.x + 200, box.y + 200);
    await page.waitForTimeout(100);
    
    // Select the drawn shape
    await page.mouse.click(box.x + 200, box.y + 200);
    await page.waitForTimeout(100);
    
    // Click '글상자로' (btn_add_text_to_shape)
    await page.click('#btn_add_text_to_shape');
    await page.waitForTimeout(100);
    
    console.log("--- BEFORE FIRST CLICK ---");
    // Click canvas elsewhere to deselect
    await page.mouse.click(box.x + 10, box.y + 10);
    await page.waitForTimeout(300);
    
    console.log("--- FIRST CLICK (Select Shape) ---");
    // Click the shape once
    await page.mouse.click(box.x + 200, box.y + 200);
    await page.waitForTimeout(400); // wait > 300ms
    
    console.log("--- SECOND CLICK (Enter Text Edit) ---");
    // Click the shape again (should enter edit)
    await page.mouse.click(box.x + 200, box.y + 200);
    await page.waitForTimeout(300);
    
    // Check if editing mode is active
    const isEditing = await page.evaluate(() => {
        const textObj = window.canvas.getObjects().find(o => o.type === 'textbox');
        return textObj && textObj.isEditing;
    });
    
    console.log("Is text editing?", isEditing);
    
    await browser.close();
})();
