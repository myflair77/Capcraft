window.prepareRenderingScene = async function () {
    activeTool = null;
    canvas.isDrawingMode = false;
    isHistoryAction = true;
    canvas.clear(); recentList = []; activeRecentIdx = -1;
    commitLoadToCanvas(null, 1000, 700, '#e4eef8');
    const tile = document.createElement('canvas'); tile.width = tile.height = 100;
    const ctx = tile.getContext('2d');
    ctx.fillStyle = '#267cba'; ctx.fillRect(0, 0, 100, 100);
    ctx.fillStyle = '#ffe477'; ctx.fillRect(20, 20, 60, 60);
    const src = tile.toDataURL();
    const makeImage = () => new Promise(resolve => fabric.Image.fromURL(src, resolve));
    const rect = new fabric.Rect({ left: 80, top: 240, width: 140, height: 100, fill: '#ed634a', stroke: '#843422', strokeWidth: 3 });
    const emoji = await makeImage(); emoji.set({ left: 300, top: 240, isEmoji: true });
    const image = await makeImage(); image.set({ left: 520, top: 240, isMediaImage: true });
    const mosaic = await makeImage(); mosaic.set({ left: 740, top: 240, isMosaic: true });
    window.renderingObjects = [rect, emoji, image, mosaic];
    canvas.add(...renderingObjects);
    ['도형', '이모티콘', '이미지', '모자이크'].forEach((name, i) => {
        canvas.add(new fabric.Text(name, { left: 80 + i * 220, top: 170, fontSize: 26,
            fill: '#20334d', selectable: false, evented: false }));
    });
    isHistoryAction = false; updateObjectSelectability();
    canvas.discardActiveObject(); canvas.renderAll();
};
