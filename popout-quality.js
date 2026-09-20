/* Resolution-independent popout snapshots and single-pass perspective rendering. */
window.CapcraftPopout = (() => {
    const MAX_PIXELS = 4 * 1024 * 1024;
    function drawCachedShadow(ctx, img, shadow) {
        if (!shadow || !img._element) return;
        const blur=Math.max(0, Number(shadow.blur)||0);
        const ox=Number(shadow.offsetX)||0, oy=Number(shadow.offsetY)||0;
        const angle=(Number(img.angle)||0)*Math.PI/180;
        // Canvas shadows are screen-aligned; counter-rotate their local offset.
        const dx=ox*Math.cos(angle)+oy*Math.sin(angle);
        const dy=-ox*Math.sin(angle)+oy*Math.cos(angle);
        const pad=Math.ceil(blur*2+Math.abs(dx)+Math.abs(dy)+4);
        const width=img.width+pad*2,height=img.height+pad*2;
        const key=JSON.stringify([img.width,img.height,blur,dx,dy,shadow.color]);
        let cache=img._popoutShadowCache;
        if (!cache || cache.source!==img._element || cache.key!==key) {
            // A blurred shadow has no high-frequency image detail. Building it
            // at 2x document resolution can block a recent-item switch for
            // hundreds of milliseconds. Bound only this soft mask; the actual
            // popout raster and export image retain their original resolution.
            const ratio=density(width,height,Math.min(1,512/Math.max(width,height)));
            const bitmap=document.createElement('canvas');
            bitmap.width=Math.max(1,Math.ceil(width*ratio));
            bitmap.height=Math.max(1,Math.ceil(height*ratio));
            // Build only on changes, on a CPU-backed offscreen surface. Never
            // execute a live shadow filter or read pixels from the visible canvas.
            const g=bitmap.getContext('2d',{willReadFrequently:true});
            const shift=width+img.width+pad+10;
            g.scale(ratio,ratio);
            g.shadowColor=shadow.color;
            g.shadowBlur=blur*ratio;
            g.shadowOffsetX=(shift+dx)*ratio;
            g.shadowOffsetY=dy*ratio;
            g.drawImage(img._element,pad-shift,pad,img.width,img.height);
            cache={source:img._element,key,bitmap,width:bitmap.width/ratio,height:bitmap.height/ratio,pad};
            img._popoutShadowCache=cache;
        }
        ctx.drawImage(cache.bitmap,-img.width/2-cache.pad,-img.height/2-cache.pad,cache.width,cache.height);
    }
    function density(width, height, wanted = 4) {
        return Math.max(Number.EPSILON, Math.min(wanted, Math.sqrt(MAX_PIXELS / Math.max(1, width * height)),
            8192 / Math.max(width, height)));
    }
    function surface(width, height, ratio) {
        const result = document.createElement('canvas');
        result.width = Math.max(1, Math.ceil(width * ratio));
        result.height = Math.max(1, Math.ceil(height * ratio));
        const ctx = result.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        // Diagnostic comparison must cover intermediate popout surfaces too,
        // not just fabric.Image's final draw onto the visible canvas.
        ctx.imageSmoothingQuality = new URLSearchParams(location.search).has('default-image-sampling') ? 'low' : 'high';
        return result;
    }
    function snapshot(canvas, original) {
        const bounds = original.getBoundingRect(true, true);
        const ratio = density(bounds.width, bounds.height);
        const objects = canvas._objects;
        const caches = objects.map(obj => obj.objectCaching);
        const stateKeys = ['viewportTransform', 'width', 'height', 'interactive', 'enableRetinaScaling', 'contextTop'];
        const state = Object.fromEntries(stateKeys.map(k => [k, canvas[k]]));
        try {
            // Render directly from original images/vectors, never copy the screen bitmap.
            canvas._objects = objects.filter(o => o !== original && !o.isTemp && !o.__isLineHandle);
            objects.forEach(o => { o.objectCaching = false; });
            canvas.viewportTransform = [1, 0, 0, 1, 0, 0];
            const image = canvas.toCanvasElement(ratio, bounds);
            return { image, width: bounds.width, height: bounds.height, ratio };
        } finally {
            canvas._objects = objects;
            Object.assign(canvas, state);
            canvas.calcViewportBoundaries();
            objects.forEach((o, i) => { o.objectCaching = caches[i]; });
        }
    }
    function homography(from, to) {
        const matrix = [];
        for (let i = 0; i < 4; i++) {
            const [x, y] = from[i], [u, v] = to[i];
            matrix.push([x, y, 1, 0, 0, 0, -u*x, -u*y, u]);
            matrix.push([0, 0, 0, x, y, 1, -v*x, -v*y, v]);
        }
        for (let col = 0; col < 8; col++) {
            let pivot = col;
            for (let row = col + 1; row < 8; row++) {
                if (Math.abs(matrix[row][col]) > Math.abs(matrix[pivot][col])) pivot = row;
            }
            [matrix[col], matrix[pivot]] = [matrix[pivot], matrix[col]];
            const divisor = matrix[col][col];
            if (Math.abs(divisor) < 1e-10) throw new Error('Degenerate popout perspective');
            for (let j = col; j < 9; j++) matrix[col][j] /= divisor;
            for (let row = 0; row < 8; row++) {
                if (row === col) continue;
                const factor = matrix[row][col];
                for (let j = col; j < 9; j++) matrix[row][j] -= factor * matrix[col][j];
            }
        }
        return matrix.map(row => row[8]);
    }
    function perspective(flat, width, height, tiltX, tiltY, ratio) {
        if (!tiltX && !tiltY) return { image: flat, width, height, shiftX: 0, shiftY: 0 };
        const rx = Math.max(-80, Math.min(80, tiltX)) * Math.PI / 180;
        const ry = Math.max(-80, Math.min(80, tiltY)) * Math.PI / 180;
        const distance = Math.max(width, height) * 1.5;
        const corners = [[0, 0], [width, 0], [width, height], [0, height]];
        const projected = corners.map(([u, v]) => {
            const x = u - width/2, y = v - height/2;
            const xx = x * Math.cos(ry) + y * Math.sin(rx) * Math.sin(ry);
            const yy = y * Math.cos(rx);
            const z = -x * Math.sin(ry) + y * Math.sin(rx) * Math.cos(ry);
            const scale = distance / (distance - z);
            return [xx * scale, yy * scale];
        });
        const left = Math.min(...projected.map(p => p[0])), top = Math.min(...projected.map(p => p[1]));
        const right = Math.max(...projected.map(p => p[0])), bottom = Math.max(...projected.map(p => p[1]));
        const outW = right-left, outH = bottom-top;
        ratio = density(outW, outH, ratio);
        const output = surface(outW, outH, ratio), ctx = output.getContext('2d');
        const pixels = flat.getContext('2d').getImageData(0, 0, flat.width, flat.height);
        const result = ctx.createImageData(output.width, output.height);
        const h = homography(projected, corners);
        const source = pixels.data, dest = result.data, sw = flat.width, sh = flat.height;
        // Inverse mapping visits every output pixel once: no strip overlaps/seams or repeated resampling.
        for (let y = 0; y < output.height; y++) for (let x = 0; x < output.width; x++) {
            const dx = left + (x + 0.5) * outW / output.width;
            const dy = top + (y + 0.5) * outH / output.height;
            const d = h[6]*dx + h[7]*dy + 1;
            let u = (h[0]*dx + h[1]*dy + h[2]) / d;
            let v = (h[3]*dx + h[4]*dy + h[5]) / d;
            if (u < 0 || v < 0 || u >= width || v >= height) continue;
            u = Math.max(0, Math.min(sw-1, u * sw/width - 0.5));
            v = Math.max(0, Math.min(sh-1, v * sh/height - 0.5));
            const x0 = Math.floor(u), y0 = Math.floor(v), x1 = Math.min(sw-1, x0+1), y1 = Math.min(sh-1, y0+1);
            const fx = u-x0, fy = v-y0;
            // No per-pixel arrays: large popouts otherwise create millions of short-lived allocations.
            const i0=(y0*sw+x0)*4, i1=(y0*sw+x1)*4, i2=(y1*sw+x0)*4, i3=(y1*sw+x1)*4;
            const a0=(1-fx)*(1-fy)*source[i0+3], a1=fx*(1-fy)*source[i1+3];
            const a2=(1-fx)*fy*source[i2+3], a3=fx*fy*source[i3+3];
            const a=a0+a1+a2+a3;
            const i = (y*output.width+x)*4;
            if (a) {
                for(let c=0;c<3;c++) dest[i+c]=(source[i0+c]*a0+source[i1+c]*a1+source[i2+c]*a2+source[i3+c]*a3)/a;
                dest[i+3]=a;
            }
        }
        ctx.putImageData(result, 0, 0);
        return { image: output, width: outW, height: outH, shiftX: (left+right)/2, shiftY: (top+bottom)/2 };
    }
    let nativeBlurWorks;
    function supportsNativeBlur() {
        if (nativeBlurWorks !== undefined) return nativeBlurWorks;
        const probe = document.createElement('canvas');
        probe.width = 9; probe.height = 9;
        const context = probe.getContext('2d');
        const input = document.createElement('canvas');
        input.width = input.height = 9;
        input.getContext('2d').fillRect(4, 4, 1, 1);
        context.filter = 'blur(0.6px)';
        context.drawImage(input, 0, 0);
        const alpha = context.getImageData(4, 4, 1, 1).data[3];
        return nativeBlurWorks = alpha > 0 && alpha < 255;
    }
    function blurLuminance(data, w, h, sigma) {
        const radius = Math.ceil(2 * sigma), weights = [];
        let sum = 0;
        for (let k = -radius; k <= radius; k++) {
            const weight = Math.exp(-k * k / (2 * sigma * sigma));
            weights.push(weight); sum += weight;
        }
        for (let k = 0; k < weights.length; k++) weights[k] /= sum;
        const luma = new Float32Array(w*h), horizontal = new Float32Array(w*h);
        for (let i = 0; i < luma.length; i++) {
            const p = i*4;
            luma[i] = .2126*data[p] + .7152*data[p+1] + .0722*data[p+2];
        }
        for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
            let value = 0;
            for (let k = -radius; k <= radius; k++) value += weights[k+radius]*luma[y*w+Math.max(0,Math.min(w-1,x+k))];
            horizontal[y*w+x] = value;
        }
        for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
            let value = 0;
            for (let k = -radius; k <= radius; k++) value += weights[k+radius]*horizontal[Math.max(0,Math.min(h-1,y+k))*w+x];
            luma[y*w+x] = value;
        }
        return luma;
    }
    function sharpen(source, strength, sourceWidth) {
        const output = surface(source.width, source.height, 1), ctx = output.getContext('2d');
        ctx.drawImage(source, 0, 0);
        if (!strength) return output;
        const pixels = ctx.getImageData(0, 0, output.width, output.height), data = pixels.data;
        const w = output.width, h = output.height;
        const sigma = Math.max(.5, Math.min(2.4, .6*w/sourceWidth));
        let soft, softLuma;
        if (supportsNativeBlur()) {
            const blurred = surface(w, h, 1), blurContext = blurred.getContext('2d');
            blurContext.filter = `blur(${sigma}px)`;
            blurContext.drawImage(source, 0, 0);
            soft = blurContext.getImageData(0, 0, w, h).data;
        } else {
            // Some Qt software-compositor configurations silently ignore Canvas filters.
            // Only regenerated popouts pay this cost; movement still uses cached pixels.
            softLuma = blurLuminance(data, w, h, sigma);
        }
        for (let i=0; i<w*h; i++) {
            const p=i*4;
            const edge=softLuma ? .2126*data[p]+.7152*data[p+1]+.0722*data[p+2]-softLuma[i]
                : .2126*(data[p]-soft[p])+.7152*(data[p+1]-soft[p+1])+.0722*(data[p+2]-soft[p+2]);
            // Preserve alpha and color differences; limit halos and leave flat areas untouched.
            if (Math.abs(edge)<3 || data[i*4+3]!==255) continue;
            let delta=Math.max(-12,Math.min(12,edge*strength/100*1.5));
            delta=Math.max(-Math.min(data[i*4],data[i*4+1],data[i*4+2]), Math.min(delta,255-Math.max(data[i*4],data[i*4+1],data[i*4+2])));
            for(let c=0;c<3;c++) data[i*4+c]+=delta;
        }
        ctx.putImageData(pixels,0,0);
        return output;
    }
    function trimTransparentBounds(result, img, geometryKey) {
        const raster = result.image, sx = raster.width / result.width, sy = raster.height / result.height;
        let bounds = img._popoutTightBoundsKey === geometryKey ? img._popoutTightBounds : null;
        if (!bounds) {
            const pixels = raster.getContext('2d').getImageData(0, 0, raster.width, raster.height).data;
            let left=raster.width, top=raster.height, right=-1, bottom=-1;
            for(let y=0;y<raster.height;y++) for(let x=0;x<raster.width;x++) {
                if(pixels[(y*raster.width+x)*4+3]===0) continue;
                left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);
            }
            if(right<left) return result;
            // Bounds belong to logical geometry, not raster density. Reuse them when
            // sharpening or resizing so supersampling cannot move the fixed handle.
            bounds={left:left/sx,top:top/sy,width:(right-left+1)/sx,height:(bottom-top+1)/sy};
            img._popoutTightBoundsKey=geometryKey;
            img._popoutTightBounds=bounds;
        }
        const image=surface(bounds.width,bounds.height,Math.max(sx,sy));
        image.getContext('2d').drawImage(raster,bounds.left*sx,bounds.top*sy,bounds.width*sx,bounds.height*sy,
            0,0,image.width,image.height);
        return {image,width:bounds.width,height:bounds.height,
            shiftX:result.shiftX+bounds.left+bounds.width/2-result.width/2,
            shiftY:result.shiftY+bounds.top+bounds.height/2-result.height/2};
    }

    function regenerate(img, reuseExisting = false) {
        if (!img._croppedBg || !img.linkedOriginal) return;
        const sourceW = img._popoutSourceWidth || img._croppedBg.width;
        const sourceH = img._popoutSourceHeight || img._croppedBg.height;
        const border = Math.max(0, img.popoutBorder ?? 8), pad = border + 2;
        const width = sourceW + pad*2, height = sourceH + pad*2;
        const requested = Math.min(4, Math.max(2, Math.abs(img.scaleX || 1), Math.abs(img.scaleY || 1)));
        const ratio = density(width, height, requested);
        const strength = Math.max(0, Math.min(100, Number(img.popoutSharpness) || 0));
        const mask = img.linkedOriginal;
        const key = JSON.stringify([width, height, ratio, strength, img.tiltX, img.tiltY,
            img.popoutBorderColor, mask.width, mask.height, mask.scaleX, mask.scaleY,
            mask.angle, mask.skewX, mask.skewY, mask.flipX, mask.flipY, mask.rx, mask.ry,
            mask.path, mask.points]);
        if (reuseExisting && img._element) {
            // Older saved popouts include the uncropped projection canvas.
            // Rebuild them on the next rotation/property edit instead of treating it as current.
            img._popoutRenderKey = img._popoutTightBounds ? key : null;
            img._popoutRenderSource = img._croppedBg;
            img._lastBorder = img.popoutBorder;
            img._currentShiftX = img.left - (img._baseLeft ?? img.left);
            img._currentShiftY = img.top - (img._baseTop ?? img.top);
            return;
        }
        // Position, shadow and outer rotation do not change the baked pixels.
        if (img._popoutRenderKey === key && img._popoutRenderSource === img._croppedBg) {
            img.setCoords();
            return;
        }
        if (!img._sharpSource || img._sharpSourceOriginal !== img._croppedBg || img._sharpStrength !== strength) {
            img._sharpSource = strength ? sharpen(img._croppedBg, strength, sourceW) : img._croppedBg;
            img._sharpSourceOriginal = img._croppedBg; img._sharpStrength = strength;
        }
        const flat = surface(width, height, ratio), ctx = flat.getContext('2d');
        ctx.scale(flat.width/width, flat.height/height);
        const obj = img.linkedOriginal;
        const keys = ['stroke', 'strokeWidth', 'fill', 'shadow', 'left', 'top', 'originX', 'originY', 'objectCaching'];
        const old = Object.fromEntries(keys.map(k => [k, obj[k]]));
        try {
            Object.assign(obj, { stroke: 'transparent', strokeWidth: 0, fill: 'black', shadow: null,
                left: width/2, top: height/2, originX: 'center', originY: 'center', objectCaching: false });
            obj.render(ctx);
            ctx.globalCompositeOperation = 'source-in';
            ctx.drawImage(img._sharpSource, 0, 0, img._croppedBg.width, img._croppedBg.height, pad, pad, sourceW, sourceH);
            if (border) {
                ctx.globalCompositeOperation = 'source-over'; obj.fill = 'transparent';
                obj.stroke = img.popoutBorderColor || '#ffffff'; obj.strokeWidth = border;
                obj.render(ctx);
            }
        } finally { Object.assign(obj, old); }
        const geometryKey = JSON.stringify([width,height,img.tiltX,img.tiltY,img.popoutBorderColor,
            mask.width,mask.height,mask.scaleX,mask.scaleY,mask.angle,mask.skewX,mask.skewY,
            mask.flipX,mask.flipY,mask.rx,mask.ry,mask.path,mask.points]);
        const result = trimTransparentBounds(
            perspective(flat, width, height, img.tiltX || 0, img.tiltY || 0, ratio), img, geometryKey);
        if (img._baseLeft === undefined) { img._baseLeft = img.left; img._baseTop = img.top; }
        img._currentShiftX = result.shiftX; img._currentShiftY = result.shiftY;
        img.set({ left: img._baseLeft + result.shiftX, top: img._baseTop + result.shiftY,
            width: result.width, height: result.height, dirty: true });
        img._element = img._originalElement = result.image;
        if (new URLSearchParams(location.search).has('popout-png-source')) {
            // Diagnostic: same raster dimensions and lossless PNG, but an
            // HTMLImageElement draw source instead of an HTMLCanvasElement.
            // Ignore stale decodes after another resize/regeneration.
            const raster = result.image;
            const decoded = new Image();
            decoded.onload = () => {
                if (img._element !== raster) return;
                // Keep the editable/export raster intact; change display only.
                img._popoutDisplayRaster = raster;
                img._popoutDisplayImage = decoded;
                img.dirty = true;
                if (img.canvas) img.canvas.requestRenderAll();
                console.log('POPOUT_PNG_SOURCE ' + JSON.stringify({
                    width:decoded.naturalWidth,height:decoded.naturalHeight,
                    sameSize:decoded.naturalWidth===raster.width&&decoded.naturalHeight===raster.height}));
            };
            decoded.onerror = () => console.warn('POPOUT_PNG_SOURCE decode failed; keeping raster');
            decoded.src = raster.toDataURL('image/png');
        }
        img._popoutRasterScale = result.image.width / result.width;
        img._popoutRenderedScale = requested;
        img._lastBorder = img.popoutBorder;
        img._popoutRenderKey = key;
        img._popoutRenderSource = img._croppedBg;
        img.setCoords();
    }
    return { snapshot, regenerate, density, sharpen, drawCachedShadow, adopt: img => regenerate(img, true) };
})();
