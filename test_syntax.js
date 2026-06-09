
        // Chromium/Fabric.js textBaseline 버그 패치 ('alphabetical' -> 'alphabetic')
        const originalTextBaseline = Object.getOwnPropertyDescriptor(CanvasRenderingContext2D.prototype, 'textBaseline');
        if (originalTextBaseline) {
            Object.defineProperty(CanvasRenderingContext2D.prototype, 'textBaseline', {
                get: function() { return originalTextBaseline.get.call(this); },
                set: function(val) {
                    if (val === 'alphabetical') val = 'alphabetic';
                    originalTextBaseline.set.call(this, val);
                }
            });
        }
        
        // (이모티콘 패치는 개체 생성 시 fabric.Image로 변환하는 방식으로 대체됨)
        
        // 상태 관리 및 Undo/Redo 관련 변수 최우선 선언 (참조 오류 방지)
        let stateHistory = [];
        let historyIndex = -1;
        let isHistoryAction = false;
        let recentList = [];

        // 커스텀 속성 직렬화 (Undo/Redo 및 JSON 로드 시 속성 손실 방지)
        const originalToObject = fabric.Object.prototype.toObject;
        fabric.Object.prototype.toObject = function(additionalProperties) {
            return originalToObject.call(this, ['isArrowBody', 'isArrowHead', 'isEmoji', 'isMosaic', 'strokeDashArray', 'isMediaImage', 'arrowType', 'arrowSize'].concat(additionalProperties || []));
        };

        // 한글(IME) 입력 시 커서 위치 보정
        const _originalRenderCursor = fabric.IText.prototype.renderCursor;
        fabric.IText.prototype.renderCursor = function(boundaries, ctx) {
            let offset = 0;
            if (this.inCompositionMode && this.hiddenTextarea && this.hiddenTextarea.value) {
                let charStr = this.hiddenTextarea.value.slice(-1);
                ctx.font = this._getFontDeclaration();
                let w = ctx.measureText(charStr).width;
                offset = w || this.fontSize;
            }
            let origLeft = boundaries.left;
            boundaries.left += offset;
            _originalRenderCursor.call(this, boundaries, ctx);
            boundaries.left = origLeft;
        };

        // 글로벌 스크롤 방어
        window.addEventListener('scroll', () => { window.scrollTo(0, 0); });
        document.getElementById('workspace').addEventListener('scroll', function() { this.scrollLeft = 0; this.scrollTop = 0; });

        window.sysMosaicPx = 5;

        // 선택 개체 컨트롤 커스터마이징
        function initCustomControls() {
            const controls = fabric.Object.prototype.controls;
            
            // 모든 개체에 대해 strokeUniform 설정 (크기 조절 시 선 굵기 유지)
            fabric.Object.prototype.strokeUniform = true;
            fabric.Object.prototype.noScaleCache = false;
            
            // 기본 컨트롤 숨기기
            fabric.Object.prototype.set({
                centeredRotation: false,
                transparentCorners: false,
                cornerColor: '#3b82f6',
                cornerStrokeColor: '#ffffff',
                cornerSize: 10,
                touchCornerSize: 24,
                cornerStyle: 'circle',
                padding: 10,
                borderDashArray: [3, 3]
            });

            // 화살표 커서 설정 (resize/move)
            controls.ml.cursorStyle = 'ew-resize';
            controls.mr.cursorStyle = 'ew-resize';
            controls.mt.cursorStyle = 'ns-resize';
            controls.mb.cursorStyle = 'ns-resize';
            controls.tl.cursorStyle = 'nwse-resize';
            const rawRotateSvg = "<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8' stroke='rgba(0,0,0,0.6)' stroke-width='5'/><path d='M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8'/><path d='M21 3v5h-5' stroke='rgba(0,0,0,0.6)' stroke-width='5'/><path d='M21 3v5h-5'/></svg>";
            const rotateCursorUrl = `url(data:image/svg+xml;base64,${btoa(rawRotateSvg)}) 12 12, crosshair`;
            controls.tr.cursorStyle = rotateCursorUrl;
            controls.tr.cursorStyleHandler = function() { return rotateCursorUrl; };
            controls.bl.cursorStyle = 'nesw-resize';
            controls.br.cursorStyle = 'nwse-resize';
            // 이동 커서
            fabric.Object.prototype.moveCursor = 'move';
            fabric.Object.prototype.hoverCursor = 'move';
            fabric.IText.prototype.hoverCursor = 'text';
            fabric.Textbox.prototype.hoverCursor = 'text';

            // 회전 핸들 숨김 (mtr은 사용 안 함)
            if (controls.mtr) controls.mtr.visible = false;

            // 커서는 기본 Fabric.js 동작 사용 (Fabric 5.x 호환)

            // 이미지 개체에 대한 특별 처리 (변 드래그 시 자르기, 꼭짓점 드래그 시 크기 조절)
            function cropX(eventData, transform, x, y) {
                const target = transform.target;
                if (!target.isMediaImage) {
                    return fabric.controlsUtils.scalingX(eventData, transform, x, y);
                }
                const localPoint = fabric.controlsUtils.getLocalPoint(transform, transform.originX, transform.originY, x, y);
                const multiplier = transform.corner === 'ml' ? -1 : 1;
                
                const oldWidth = target.width;
                const newWidth = Math.max(5, (localPoint.x * multiplier) / target.scaleX);
                
                if (target.cropX === undefined) target.cropX = 0;
                
                if (transform.corner === 'ml') {
                    const diff = oldWidth - newWidth;
                    target.cropX += diff;
                    target.left += diff * target.scaleX; // 위치 보정
                }
                target.width = newWidth;
                return true;
            }

            function cropY(eventData, transform, x, y) {
                const target = transform.target;
                if (!target.isMediaImage) {
                    return fabric.controlsUtils.scalingY(eventData, transform, x, y);
                }
                const localPoint = fabric.controlsUtils.getLocalPoint(transform, transform.originX, transform.originY, x, y);
                const multiplier = transform.corner === 'mt' ? -1 : 1;
                
                const oldHeight = target.height;
                const newHeight = Math.max(5, (localPoint.y * multiplier) / target.scaleY);
                
                if (target.cropY === undefined) target.cropY = 0;
                
                if (transform.corner === 'mt') {
                    const diff = oldHeight - newHeight;
                    target.cropY += diff;
                    target.top += diff * target.scaleY; // 위치 보정
                }
                target.height = newHeight;
                return true;
            }

            controls.ml.actionHandler = cropX;
            controls.mr.actionHandler = cropX;
            controls.mt.actionHandler = cropY;
            controls.mb.actionHandler = cropY;

            // 크기 조절과 회전을 동시에 처리하는 핸들러
            function scaleAndRotate(eventData, transform, x, y) {
                const target = transform.target;
                
                if (transform.fixedPivot === undefined) {
                    transform.fixedPivot = target.translateToOriginPoint(target.getCenterPoint(), 'left', 'top');
                    transform.initialAngle = target.angle || 0;
                    transform.initialScaleX = target.scaleX || 1;
                    transform.initialScaleY = target.scaleY || 1;
                    
                    const dx = transform.ex - transform.fixedPivot.x;
                    const dy = transform.ey - transform.fixedPivot.y;
                    transform.initialDistance = Math.sqrt(dx * dx + dy * dy);
                    transform.initialMouseAngle = Math.atan2(dy, dx);
                }
                
                const pivot = transform.fixedPivot;
                const dx = x - pivot.x;
                const dy = y - pivot.y;
                const currentDistance = Math.sqrt(dx * dx + dy * dy);
                const currentMouseAngle = Math.atan2(dy, dx);
                
                let ratio = 1;
                if (transform.initialDistance > 0) {
                    ratio = currentDistance / transform.initialDistance;
                }
                
                let angleDiff = (currentMouseAngle - transform.initialMouseAngle) * 180 / Math.PI;
                let newAngle = transform.initialAngle + angleDiff;
                
                target.set({
                    scaleX: transform.initialScaleX * ratio,
                    scaleY: transform.initialScaleY * ratio,
                    angle: newAngle
                });
                
                target.setPositionByOrigin(pivot, 'left', 'top');
                
                // 툴팁 표시
                let floating = document.getElementById('floating_angle_tooltip');
                if (!floating) {
                    floating = document.createElement('div');
                    floating.id = 'floating_angle_tooltip';
                    floating.style.position = 'fixed';
                    floating.style.background = 'rgba(15,23,42,0.85)';
                    floating.style.color = '#fff';
                    floating.style.padding = '4px 8px';
                    floating.style.borderRadius = '4px';
                    floating.style.fontSize = '12px';
                    floating.style.fontWeight = 'bold';
                    floating.style.pointerEvents = 'none';
                    floating.style.zIndex = '10000';
                    document.body.appendChild(floating);
                }
                floating.style.display = 'block';
                floating.style.left = (eventData.clientX + 15) + 'px';
                floating.style.top = (eventData.clientY + 15) + 'px';
                
                let displayAngle = Math.round(newAngle) % 360;
                if (displayAngle < 0) displayAngle += 360;
                floating.innerText = displayAngle + '°';
                
                return true;
            }

            // 모서리 컨트롤 핸들러 변경 (우측 상단은 회전 전용)
            controls.tl.actionHandler = fabric.controlsUtils.scalingEqually;
            controls.bl.actionHandler = fabric.controlsUtils.scalingEqually;
            controls.br.actionHandler = fabric.controlsUtils.scalingEqually;
            controls.tr.actionHandler = function(eventData, transform, x, y) {
                transform.originX = 'left';
                transform.originY = 'top';
                return fabric.controlsUtils.rotationWithSnapping(eventData, transform, x, y);
            };

            const rotateIconSvg = "data:image/svg+xml;utf8," + encodeURIComponent("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='18' height='18'><circle cx='12' cy='12' r='11' fill='white' stroke='#3b82f6' stroke-width='2'/><path d='M15.5 12c0 1.93-1.57 3.5-3.5 3.5s-3.5-1.57-3.5-3.5 1.57-3.5 3.5-3.5v2l3.5-3-3.5-3v2c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5h-1.5z' fill='#3b82f6'/></svg>");
            const rotateImg = new Image(); rotateImg.src = rotateIconSvg;
            
            controls.tr.render = function(ctx, left, top, styleOverride, fabricObject) {
                const size = 18;
                ctx.save();
                ctx.translate(left, top);
                ctx.drawImage(rotateImg, -size/2, -size/2, size, size);
                ctx.restore();
            };
            controls.tr.cornerSize = 18;

            // 좌우 반전 / 상하 반전 버튼 (플립) 추가
            const flipXIcon = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' rx='4' fill='white' stroke='%233b82f6' stroke-width='2'/><line x1='12' y1='5' x2='12' y2='19' stroke='%233b82f6' stroke-width='1.5'/><polygon points='10,12 5,8 5,16' fill='%233b82f6'/><polygon points='14,12 19,8 19,16' fill='%233b82f6'/></svg>";
            const flipYIcon = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' rx='4' fill='white' stroke='%233b82f6' stroke-width='2'/><line x1='5' y1='12' x2='19' y2='12' stroke='%233b82f6' stroke-width='1.5'/><polygon points='12,10 8,5 16,5' fill='%233b82f6'/><polygon points='12,14 8,19 16,19' fill='%233b82f6'/></svg>";

            const flipXImg = new Image(); flipXImg.src = flipXIcon;
            const flipYImg = new Image(); flipYImg.src = flipYIcon;

            function renderFlipX(ctx, left, top, styleOverride, fabricObject) {
                const size = 40;
                ctx.save();
                ctx.translate(left, top);
                ctx.drawImage(flipXImg, -size/2, -size/2, size, size);
                ctx.restore();
            }
            function renderFlipY(ctx, left, top, styleOverride, fabricObject) {
                const size = 40;
                ctx.save();
                ctx.translate(left, top);
                ctx.drawImage(flipYImg, -size/2, -size/2, size, size);
                ctx.restore();
            }

            controls.flipX = new fabric.Control({
                x: 0, y: -0.5, offsetY: -40, offsetX: -100, cursorStyle: 'pointer',
                mouseDownHandler: function(eventData, transform, x, y) {
                    const target = transform.target;
                    const center = target.getCenterPoint();
                    target.set('flipX', !target.flipX);
                    target.setPositionByOrigin(center, 'center', 'center');
                    target.setCoords();
                    target.set('dirty', true);
                    if (target.canvas) {
                        target.canvas.fire('object:modified', { target: target });
                        target.canvas.requestRenderAll();
                    }
                    return true;
                },
                actionName: 'flipX',
                render: renderFlipX,
                sizeX: 60, sizeY: 60, cornerSize: 60, touchCornerSize: 60, transparentCorners: false
            });

            
            const addTextIcon = "data:image/svg+xml;utf8," + encodeURIComponent("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' rx='4' fill='white' stroke='#3b82f6' stroke-width='2'/><path d='M7 7h10v2h-4v8h-2v-8H7V7z' fill='#3b82f6'/></svg>");
            const addTextImg = new Image(); addTextImg.src = addTextIcon;

            controls.addText = new fabric.Control({
                x: 0, y: -0.5, offsetY: -40, offsetX: 100, cursorStyle: 'pointer',
                mouseDownHandler: function(eventData, transform, x, y) {
                    const target = transform.target;
                    if (['rect', 'ellipse', 'polygon'].includes(target.type) && !target.linkedText) {
                        document.getElementById('btn_add_text_to_shape').click();
                    }
                    return true;
                },
                actionName: 'addText',
                render: function(ctx, left, top, styleOverride, fabricObject) {
                    if (['rect', 'ellipse', 'polygon'].includes(fabricObject.type) && !fabricObject.linkedText) {
                        const size = 40;
                        ctx.save();
                        ctx.translate(left, top);
                        ctx.drawImage(addTextImg, -size/2, -size/2, size, size);
                        ctx.restore();
                    }
                },
                sizeX: 60, sizeY: 60, cornerSize: 60, touchCornerSize: 60, transparentCorners: false
            });

            controls.flipY = new fabric.Control({
                x: 0, y: -0.5, offsetY: -40, offsetX: -50, cursorStyle: 'pointer',
                mouseDownHandler: function(eventData, transform, x, y) {
                    const target = transform.target;
                    const center = target.getCenterPoint();
                    target.set('flipY', !target.flipY);
                    target.setPositionByOrigin(center, 'center', 'center');
                    target.setCoords();
                    target.set('dirty', true);
                    if (target.canvas) {
                        target.canvas.fire('object:modified', { target: target });
                        target.canvas.requestRenderAll();
                    }
                    return true;
                },
                actionName: 'flipY',
                render: renderFlipY,
                sizeX: 60, sizeY: 60, cornerSize: 60, touchCornerSize: 60, transparentCorners: false
            });

            const sendBackIcon = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' rx='4' fill='white' stroke='%233b82f6' stroke-width='2'/><rect x='10' y='6' width='8' height='8' fill='none' stroke='%2394a3b8' stroke-width='1.5'/><rect x='6' y='10' width='8' height='8' fill='%233b82f6'/></svg>";
            const bringFrontIcon = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' rx='4' fill='white' stroke='%233b82f6' stroke-width='2'/><rect x='6' y='10' width='8' height='8' fill='none' stroke='%2394a3b8' stroke-width='1.5'/><rect x='10' y='6' width='8' height='8' fill='%233b82f6'/></svg>";

            const sendBackImg = new Image(); sendBackImg.src = sendBackIcon;
            const bringFrontImg = new Image(); bringFrontImg.src = bringFrontIcon;

            controls.sendBack = new fabric.Control({
                x: 0, y: -0.5, offsetY: -40, offsetX: 0, cursorStyle: 'pointer',
                mouseDownHandler: function(eventData, transform, x, y) {
                    const target = transform.target;
                    if (target.canvas) {
                        target._skipBringToFront = true;
                        if (target.linkedText) {
                            target.canvas.sendToBack(target.linkedText);
                            target.canvas.sendToBack(target);
                        } else if (target.linkedShape) {
                            target.canvas.sendToBack(target);
                            target.canvas.sendToBack(target.linkedShape);
                        } else {
                            target.canvas.sendToBack(target);
                        }
                        target.canvas.requestRenderAll();
                    }
                    return true;
                },
                actionName: 'sendBack',
                render: function(ctx, left, top, styleOverride, fabricObject) {
                    const size = 40;
                    ctx.save();
                    ctx.translate(left, top);
                    ctx.drawImage(sendBackImg, -size/2, -size/2, size, size);
                    ctx.restore();
                },
                sizeX: 60, sizeY: 60, cornerSize: 60, touchCornerSize: 60, transparentCorners: false
            });

            controls.bringFront = new fabric.Control({
                x: 0, y: -0.5, offsetY: -40, offsetX: 50, cursorStyle: 'pointer',
                mouseDownHandler: function(eventData, transform, x, y) {
                    const target = transform.target;
                    if (target.canvas) {
                        if (target.linkedText) {
                            target.canvas.bringToFront(target);
                            target.canvas.bringToFront(target.linkedText);
                        } else if (target.linkedShape) {
                            target.canvas.bringToFront(target.linkedShape);
                            target.canvas.bringToFront(target);
                        } else {
                            target.canvas.bringToFront(target);
                        }
                        target.canvas.requestRenderAll();
                    }
                    return true;
                },
                actionName: 'bringFront',
                render: function(ctx, left, top, styleOverride, fabricObject) {
                    const size = 40;
                    ctx.save();
                    ctx.translate(left, top);
                    ctx.drawImage(bringFrontImg, -size/2, -size/2, size, size);
                    ctx.restore();
                },
                sizeX: 60, sizeY: 60, cornerSize: 60, touchCornerSize: 60, transparentCorners: false
            });

            // Textbox 전용 컨트롤 오버라이드 (텍스트 크기 변동 방지, 너비만 조절)
            // 각 컨트롤 객체도 개별 복사해야 원본 prototype controls를 오염시키지 않음
            const textboxControls = {};
            Object.keys(controls).forEach(key => {
                textboxControls[key] = new fabric.Control(Object.assign({}, controls[key]));
            });
            fabric.Textbox.prototype.controls = textboxControls;
            fabric.Textbox.prototype.controls.ml.actionHandler = fabric.controlsUtils.changeWidth;
            fabric.Textbox.prototype.controls.mr.actionHandler = fabric.controlsUtils.changeWidth;
            fabric.Textbox.prototype.controls.tl.actionHandler = fabric.controlsUtils.changeWidth;
            fabric.Textbox.prototype.controls.bl.actionHandler = fabric.controlsUtils.changeWidth;
            fabric.Textbox.prototype.controls.br.actionHandler = fabric.controlsUtils.changeWidth;
            fabric.Textbox.prototype.controls.mt.actionHandler = function(){ return false; };
            fabric.Textbox.prototype.controls.mb.actionHandler = function(){ return false; };


            window.addEventListener('mouseup', () => {
                let floating = document.getElementById('floating_angle_tooltip');
                if (floating) floating.style.display = 'none';
            });
        }
        initCustomControls();



        const canvas = new fabric.Canvas('mainCanvas', {
            uniformScaling: false, 
            width: 800, height: 600, selection: true, 
            imageSmoothingEnabled: false,
            perPixelTargetFind: false,
            targetFindTolerance: 15,
            preserveObjectStacking: true,
            enableRetinaScaling: false
        });

        // 엣지 글로우 토글 핸들러 (선택 시 파란 테두리 및 컨트롤 표시)
        function toggleEdgeGlow(e, isActive) {
            const objs = e.selected || e.deselected || [];
            objs.forEach(obj => {
                obj.set({
                    hasBorders: isActive,
                    hasControls: isActive,
                    borderColor: '#3b82f6',
                    borderScaleFactor: 2
                });
                
                // 이미지 개체의 경우 변(Side) 컨트롤 활성화
                if(obj.isMediaImage) {
                    obj.setControlsVisibility({
                        tl: true, tr: true, br: true, bl: true,
                        ml: true, mt: true, mr: true, mb: true,
                        mtr: false, flipX: true, flipY: true, sendBack: true, bringFront: true
                    });
                } else {
                    obj.setControlsVisibility({
                        tl: true, tr: true, br: true, bl: true,
                        ml: true, mt: true, mr: true, mb: true,
                        mtr: false, flipX: true, flipY: true, sendBack: true, bringFront: true
                    });
                }
                obj.set('dirty', true);
            });
        }

        
        canvas.on('selection:created', updateObjectControls);
        canvas.on('selection:updated', updateObjectControls);
        
        function updateObjectControls(e) {
            const obj = e.selected[0];
            if (!obj) return;
            if (['rect', 'ellipse', 'polygon'].includes(obj.type) && !obj.linkedText) {
                obj.setControlVisible('addText', true);
            } else {
                obj.setControlVisible('addText', false);
            }
        }

        canvas.on('selection:created', (e) => { toggleEdgeGlow(e, true); canvas.requestRenderAll(); });
        canvas.on('selection:updated', (e) => { 
            toggleEdgeGlow({ deselected: e.deselected }, false);
            toggleEdgeGlow({ selected: e.selected }, true);
            canvas.requestRenderAll(); 
        });
        canvas.on('selection:cleared', (e) => { toggleEdgeGlow(e, false); canvas.requestRenderAll(); });

        // 단축키 (Delete, Backspace 삭제 및 개별 Copy & Paste) - 모달 방어벽 추가
        let myClipboard = null;
        let lastCanvasClick = { x: 100, y: 100 };

        window.addEventListener('keydown', (e) => {
            const isModalOpen = document.getElementById('overlay').style.display === 'block';
            const activeEl = document.activeElement;
            const isInputFocused = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT');
            
            // 모달창이 열려있거나 인풋 창에 포커스 되어 있다면 캔버스 단축키 절대 작동 방지
            if (isInputFocused || isModalOpen) return; 

            const activeObj = canvas.getActiveObject();
            if (activeObj && activeObj.isEditing) return; 

            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (activeObj) {
                    canvas.getActiveObjects().forEach(obj => canvas.remove(obj));
                    canvas.discardActiveObject();
                    saveHistory();
                }
            } else if (e.key === 'c' && (e.ctrlKey || e.metaKey)) {
                if (activeObj) {
                    activeObj.clone(cloned => { myClipboard = cloned; });
                }
            } else if (e.key === 'x' && (e.ctrlKey || e.metaKey)) {
                if (activeObj) {
                    activeObj.clone(cloned => { myClipboard = cloned; });
                    canvas.getActiveObjects().forEach(obj => canvas.remove(obj));
                    canvas.discardActiveObject();
                    saveHistory();
                }
            } else if (e.key === 'v' && (e.ctrlKey || e.metaKey)) {
                if (myClipboard) {
                    myClipboard.clone(clonedObj => {
                        canvas.discardActiveObject();
                        clonedObj.set({ 
                            left: lastCanvasClick.x, top: lastCanvasClick.y, 
                            evented: true, selectable: true 
                        });
                        if (clonedObj.type === 'activeSelection') {
                            clonedObj.canvas = canvas;
                            clonedObj.forEachObject(obj => canvas.add(obj));
                            clonedObj.setCoords();
                        } else {
                            canvas.add(clonedObj);
                        }
                        myClipboard.top += 10; 
                        myClipboard.left += 10;
                        canvas.setActiveObject(clonedObj);
                        canvas.bringToFront(clonedObj);
                        canvas.requestRenderAll();
                        saveHistory();
                    });
                }
            }
        });

        // 모달창 헤더 드래그 앤 드롭 이동 기능
        document.querySelectorAll('.modal').forEach(modal => {
            const header = modal.querySelector('.modal-header');
            if (!header) return;
            
            let isDraggingModal = false, startX, startY, initLeft, initTop;
            
            header.addEventListener('mousedown', e => {
                if (e.target.tagName === 'BUTTON' || e.target.classList.contains('modal-close')) return;
                isDraggingModal = true;
                startX = e.clientX; startY = e.clientY;
                const rect = modal.getBoundingClientRect();
                modal.style.transform = 'none';
                modal.style.left = rect.left + 'px';
                modal.style.top = rect.top + 'px';
                initLeft = rect.left; initTop = rect.top;
            });
            
            window.addEventListener('mousemove', e => {
                if (isDraggingModal) {
                    modal.style.left = (initLeft + e.clientX - startX) + 'px';
                    modal.style.top = (initTop + e.clientY - startY) + 'px';
                }
            });
            window.addEventListener('mouseup', () => { isDraggingModal = false; });
        });

        window.openModal = function(id) { 
            document.getElementById('overlay').style.display = 'block'; 
            const m = document.getElementById(id);
            m.style.transform = 'translate(-50%, -50%)';
            m.style.left = '50%';
            m.style.top = '50%';
            m.style.display = 'block'; 
        }

        window.closeModals = function() { 
            document.getElementById('overlay').style.display = 'none'; 
            document.querySelectorAll('.modal').forEach(m => m.style.display = 'none'); 
        }

        window.openGuide = async function() {
            if (pyBackend) {
                pyBackend.get_guide_html((html) => {
                    document.querySelector('#modal_guide .guide-content').innerHTML = html;
                    openModal('modal_guide');
                });
            } else {
                document.querySelector('#modal_guide .guide-content').innerHTML = '<p>백엔드에 연결되지 않았습니다.</p>';
                openModal('modal_guide');
            }
        };

        // 모자이크 서브툴바 ↔ 설정 모달 동기화
        document.getElementById('mosaic_intensity').addEventListener('input', (e) => { 
            sysMosaicPx = parseInt(e.target.value) || 5; 
            document.getElementById('set_mosaic_px').value = sysMosaicPx; 
        });
        document.getElementById('set_mosaic_px').addEventListener('input', (e) => { 
            sysMosaicPx = parseInt(e.target.value) || 5; 
            document.getElementById('mosaic_intensity').value = sysMosaicPx; 
        });

        document.getElementById('set_pen_highlighter_opacity').addEventListener('input', (e) => {
            let opacity = parseInt(e.target.value) || 30;
            let hlColor = document.getElementById('set_pen_highlighter_color').style.backgroundColor;
            document.getElementById('set_pen_highlighter_color').style.backgroundColor = new fabric.Color(hlColor).setAlpha(opacity / 100).toRgba();
        });

        // ==========================================
        // 커스텀 다이얼로그 시스템
        // ==========================================
        function customAlert(msg) {
            return new Promise(resolve => {
                document.getElementById('dialog_title').innerText = '알림';
                document.getElementById('dialog_msg').innerText = msg;
                document.getElementById('dialog_btn_cancel').style.display = 'none';
                document.getElementById('dialog_btn_ok').innerText = '확인';
                openModal('modal_custom_dialog');
                document.getElementById('dialog_btn_ok').onclick = () => { closeDialog(); resolve(true); };
            });
        }

        function customConfirm(msg) {
            return new Promise(resolve => {
                document.getElementById('dialog_title').innerText = '확인 필요';
                document.getElementById('dialog_msg').innerText = msg;
                document.getElementById('dialog_btn_cancel').style.display = 'block';
                document.getElementById('dialog_btn_ok').innerText = '예';
                document.getElementById('dialog_btn_cancel').innerText = '아니오';
                openModal('modal_custom_dialog');
                document.getElementById('dialog_btn_ok').onclick = () => { closeDialog(); resolve(true); };
                document.getElementById('dialog_btn_cancel').onclick = () => { closeDialog(); resolve(false); };
            });
        }

        window.closeDialog = function() {
            document.getElementById('modal_custom_dialog').style.display = 'none';
            if (document.querySelectorAll('.modal[style*="display: block"]').length === 0) {
                document.getElementById('overlay').style.display = 'none';
            }
        }

        // ==========================================
        // 1. 캔버스 뷰포트 초기화
        // ==========================================
        const wrapper = document.getElementById('canvas_container_wrapper');
        const canvasContainer = document.getElementById('canvas_container');
        const workspace = document.getElementById('workspace');

        let hasActiveCanvas = false;
        let currentZoom = 1.0; 
        let panX = 0; let panY = 0;

        function applyCanvasClipping() {
            canvas.clipPath = null;
            canvas.requestRenderAll();
        }

        function updateCanvasTransform() {
            wrapper.style.setProperty('--pan-x', panX + 'px');
            wrapper.style.setProperty('--pan-y', panY + 'px');
            wrapper.style.setProperty('--zoom', currentZoom);
            // calcOffset은 변환 완료 후 1회만 실행, 이중 rAF로 레이아웃 안정 후 호출
            if (window._calcOffsetRaf) cancelAnimationFrame(window._calcOffsetRaf);
            window._calcOffsetRaf = requestAnimationFrame(() => {
                requestAnimationFrame(() => { canvas.calcOffset(); });
            });
        }

        function prepareCanvasDisplay() {
            if (canvasContainer.style.display !== 'block') {
                canvasContainer.style.display = 'block';
                // Reflow는 rAF 내에서 수행하여 현재 프레임의 레이아웃 스래싱 방지
                requestAnimationFrame(() => { void canvasContainer.offsetWidth; });
            }
        }

        // ★ Fabric.js 내부 canvas-container 높이를 동기화하여 하단 깜빡임 원천 차단
        function syncFabricContainerSize() {
            const fabricWrapper = canvasContainer.querySelector('.canvas-container');
            if (fabricWrapper) {
                fabricWrapper.style.width  = canvas.width  + 'px';
                fabricWrapper.style.height = canvas.height + 'px';
            }
            canvasContainer.style.width  = canvas.width  + 'px';
            canvasContainer.style.height = canvas.height + 'px';
        }



        workspace.addEventListener('wheel', function(opt) {
            if(!hasActiveCanvas) return;
            opt.preventDefault();
            if (opt.ctrlKey) {
                let oldZoom = currentZoom;
                let newZoom = oldZoom * (0.999 ** opt.deltaY);
                if (newZoom > 10) newZoom = 10; 
                if (newZoom < 0.1) newZoom = 0.1;
                
                let wsRect = workspace.getBoundingClientRect();
                let C_x = 0; let C_y = 0;
                let scaledW = canvas.width * newZoom; let scaledH = canvas.height * newZoom;
                let mouseX = (opt.clientX - wsRect.left) - (wsRect.width / 2);
                let mouseY = (opt.clientY - wsRect.top) - (wsRect.height / 2);

                let originX = mouseX; let originY = mouseY;
                if (scaledW <= wsRect.width) originX = C_x;
                if (scaledH <= wsRect.height) originY = C_y;

                let zoomRatio = newZoom / oldZoom;
                panX = originX - (originX - panX) * zoomRatio;
                panY = originY - (originY - panY) * zoomRatio;

                if (scaledW <= wsRect.width) panX = 0;
                if (scaledH <= wsRect.height) panY = 0;

                currentZoom = newZoom;
            } else {
                // 수직/수평 스크롤 처리
                panY -= opt.deltaY;
                let scaledH = canvas.height * currentZoom;
                let wsRect = workspace.getBoundingClientRect();
                if (scaledH <= wsRect.height) {
                    panY = 0;
                } else {
                    let maxPan = (scaledH - wsRect.height) / 2 + 50;
                    if (panY > maxPan) panY = maxPan;
                    if (panY < -maxPan) panY = -maxPan;
                }
            }
            updateCanvasTransform();
        });

        let isPanning = false; let panStartX, panStartY, startPanX, startPanY;
        workspace.addEventListener('mousedown', (e) => {
            if (!activeTool && !e.target.closest('#toolbar') && !e.target.closest('.modal') && hasActiveCanvas) {
                const target = canvas.findTarget(e, false);
                if (target && target.selectable) return; 

                isPanning = true; 
                panStartX = e.clientX; panStartY = e.clientY;
                startPanX = panX; startPanY = panY;
                workspace.style.cursor = 'grabbing';
            }
        });
        workspace.addEventListener('mousemove', (e) => {
            if(!isPanning) return;
            e.preventDefault(); 
            panX = startPanX + (e.clientX - panStartX);
            panY = startPanY + (e.clientY - panStartY);
            updateCanvasTransform();
        });
        window.addEventListener('mouseup', () => { isPanning = false; updateGlobalCursor(); });

        
        function syncShapeToText(shape, transform) {
            if (!shape || !shape.linkedText) return;
            const textObj = shape.linkedText;
            const padding = 20;
            const minW = textObj.dynamicMinWidth || 50;
            
            // Calculate available text width inside the shape
            let shapeVisualW = shape.width * shape.scaleX;
            let textAreaFactor = 1;
            if (shape.type === 'ellipse') textAreaFactor = Math.cos(Math.PI / 4);
            else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) textAreaFactor = 0.5;
            let availTextW = shapeVisualW * textAreaFactor - padding;
            
            // Clamp minimum width: prevent shape from being smaller than text needs
            let minShapeW = (minW + padding) / textAreaFactor;
            if (shapeVisualW < minShapeW) {
                shape.scaleX = minShapeW / shape.width;
                shapeVisualW = minShapeW;
                availTextW = minW;
            }
            
            textObj.set({ width: Math.max(minW, availTextW) });
            
            // Calculate required height for text and clamp shape height
            let reqTextH = textObj.calcTextHeight() + padding;
            let heightFactor = 1;
            if (shape.type === 'ellipse') heightFactor = Math.cos(Math.PI / 4);
            else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) heightFactor = 0.5;
            let minShapeH = reqTextH / heightFactor;
            let shapeVisualH = shape.height * shape.scaleY;
            
            if (shapeVisualH < minShapeH) {
                shape.scaleY = minShapeH / shape.height;
            }
            
            // Sync text position and angle to shape center
            const center = shape.getCenterPoint();
            textObj.set({ left: center.x, top: center.y, angle: shape.angle });
            textObj.setCoords();
        }

        canvas.on('object:scaling', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                syncShapeToText(obj, e.transform);
                if (obj.canvas) obj.canvas.renderAll();
            }
        });

        canvas.on('object:rotating', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                const center = obj.getCenterPoint();
                obj.linkedText.set({ left: center.x, top: center.y, angle: obj.angle });
                obj.linkedText.setCoords();
                canvas.renderAll(); // Use synchronous render to prevent 1-frame visual lag
            } else if (obj.linkedShape) {
                const center = obj.getCenterPoint();
                obj.linkedShape.set({ angle: obj.angle });
                obj.linkedShape.setPositionByOrigin(new fabric.Point(center.x, center.y), 'center', 'center');
                obj.linkedShape.setCoords();
                canvas.renderAll();
            }
        });
        
        canvas.on('object:moving', (e) => {
            const obj = e.target; 
            const cw = canvas.width;
            const ch = canvas.height;
            
            const objW = (obj.width || 0) * (obj.scaleX || 1);
            const objH = (obj.height || 0) * (obj.scaleY || 1);
            
            const rad = (obj.angle || 0) * Math.PI / 180;
            const sin = Math.abs(Math.sin(rad));
            const cos = Math.abs(Math.cos(rad));
            const boundW = objW * cos + objH * sin;
            const boundH = objW * sin + objH * cos;
            
            let center = obj.getCenterPoint();
            let clamped = false;
            
            if (boundW <= cw) {
                const minX = boundW / 2;
                const maxX = cw - boundW / 2;
                if (center.x < minX) { center.x = minX; clamped = true; }
                else if (center.x > maxX) { center.x = maxX; clamped = true; }
            }
            if (boundH <= ch) {
                const minY = boundH / 2;
                const maxY = ch - boundH / 2;
                if (center.y < minY) { center.y = minY; clamped = true; }
                else if (center.y > maxY) { center.y = maxY; clamped = true; }
            }
            
            if (clamped) {
                obj.setPositionByOrigin(center, 'center', 'center');
            }
            
            if (obj.linkedText) {
                const center = obj.getCenterPoint();
                obj.linkedText.set({ left: center.x, top: center.y, angle: obj.angle });
                obj.linkedText.setCoords();
                canvas.renderAll();
            } else if (obj.linkedShape) {
                const center = obj.getCenterPoint();
                obj.linkedShape.set({ angle: obj.angle });
                obj.linkedShape.setPositionByOrigin(new fabric.Point(center.x, center.y), 'center', 'center');
                obj.linkedShape.setCoords();
            }
        });

        function commitLoadToCanvas(img, w, h, bgColor) {
            prepareCanvasDisplay();
            canvas.setWidth(w);
            canvas.setHeight(h);
            syncFabricContainerSize();
            
            function finalizeLoad() {
                hasActiveCanvas = true;
                syncFabricContainerSize();
                enableTools();
                applyFitZoom();
                applyCanvasClipping();
                isHistoryAction = false;
                saveHistory();
                pushCurrentToRecent(); // ★ 즉시 최근 목록에 추가
                renderRecentList();
            }

            if (img) {
                canvas.setBackgroundImage(img, () => {
                    canvas.renderAll();
                    finalizeLoad();
                    setTimeout(() => canvas.requestRenderAll(), 50);
                });
            } else {
                canvas.setBackgroundImage(null, () => {
                    canvas.setBackgroundColor(bgColor || 'white', () => {
                        canvas.renderAll();
                        finalizeLoad();
                        setTimeout(() => canvas.requestRenderAll(), 50);
                    });
                });
            }
        }

        function applyFitZoom() {
            if (!hasActiveCanvas) return;
            let wsRect = workspace.getBoundingClientRect();
            let fitZoom = (wsRect.width - 40) / canvas.width; 
            if (canvas.height * fitZoom > wsRect.height - 40) { fitZoom = (wsRect.height - 40) / canvas.height; }
            if(fitZoom > 1.0) fitZoom = 1.0; 
            currentZoom = fitZoom; panX = 0; panY = 0;
            updateCanvasTransform();
        }

        function pushCurrentToRecent() {
            if (!hasActiveCanvas) return;
            if (canvas.getObjects().length === 0 && !canvas.backgroundImage && (!canvas.backgroundColor || canvas.backgroundColor === 'transparent')) return;
            
            const thumbMult = Math.min(200 / Math.max(10, canvas.width), 1.0);
            const thumb = canvas.toDataURL({format:'png', multiplier: thumbMult});
            const json  = JSON.stringify(canvas);
            
            // 배경 이미지 URL 및 배경색 추출
            const bgImg = canvas.backgroundImage;
            let bgSrc = null;
            if (bgImg && bgImg.getSrc) bgSrc = bgImg.getSrc();
            const bgColor = canvas.backgroundColor;
            
            // ★ 배경 이미지 HTMLImageElement 캐싱 (loadFromJSON 우회용)
            let bgImgCache = null;
            if (bgImg && bgImg._element) {
                bgImgCache = bgImg._element; // 이미 디코딩된 Image 객체 재사용
            }
            
            // ★ 배경 제거된 경량 JSON 생성 (loadFromJSON 고속화)
            let jsonLight = null;
            try {
                const parsed = JSON.parse(json);
                if (parsed.backgroundImage) {
                    delete parsed.backgroundImage;
                    jsonLight = JSON.stringify(parsed);
                }
            } catch(e) { /* fallback: jsonLight = null → 기존 json 사용 */ }
            
            // ★ activeRecentIdx 항목 갱신 (복제 방지)
            if (activeRecentIdx >= 0 && activeRecentIdx < recentList.length) {
                recentList[activeRecentIdx].thumb = thumb;
                recentList[activeRecentIdx].json  = json;
                recentList[activeRecentIdx].jsonLight = jsonLight;
                recentList[activeRecentIdx].bgSrc = bgSrc;
                recentList[activeRecentIdx].bgColor = bgColor;
                recentList[activeRecentIdx].bgImgCache = bgImgCache;
                recentList[activeRecentIdx].width  = canvas.width;
                recentList[activeRecentIdx].height = canvas.height;
                renderRecentList();
                return;
            }

            // 중복 방지: 앞 항목과 동일하면 무시
            if (recentList.length > 0 && recentList[0].json === json) return;

            recentList.unshift({ thumb, json, jsonLight, bgSrc, bgColor, bgImgCache, width: canvas.width, height: canvas.height, time: Date.now() });
            activeRecentIdx = 0;

            const maxRecent = parseInt(document.getElementById('set_recent_max').value) || 100;
            if (recentList.length > maxRecent) recentList.pop();
            renderRecentList();
        }

        let recentSortOrder = 'desc'; // desc: 최신순, asc: 오래된순
        document.getElementById('btn_recent_sort').addEventListener('click', function() {
            recentSortOrder = (recentSortOrder === 'desc' ? 'asc' : 'desc');
            this.innerText = (recentSortOrder === 'desc' ? '최신순' : '과거순');
            renderRecentList();
        });

        function renderRecentList() {
            if (typeof triggerHistorySave === 'function') triggerHistorySave();
            const container = document.getElementById('recent_list_container');
            container.innerHTML = '';
            
            let displayList = [...recentList];
            if (recentSortOrder === 'asc') displayList.reverse();

            displayList.forEach((item, idx) => {
                // displayList상의 idx → recentList에서의 실제 인덱스
                const realIdx = recentSortOrder === 'desc' ? idx : recentList.length - 1 - idx;
                
                const div = document.createElement('div');
                div.className = 'recent-item';
                div.style.backgroundImage = `url(${item.thumb})`;
                
                // 생성 순서 번호 (recentList[0]이 가장 최신 → 번호 = 전체수 - realIdx)
                const num = document.createElement('div');
                num.className = 'recent-num';
                num.innerText = recentList.length - realIdx;
                div.appendChild(num);

                // 현재 작업 중인 항목: 파란 테두리
                if (realIdx === activeRecentIdx) div.classList.add('active');
                
                const delBtn = document.createElement('button');
                delBtn.className = 'btn-delete-thumb';
                delBtn.innerText = 'X';
                delBtn.onclick = (e) => {
                    e.stopPropagation(); 
                    const isDeletingActive = (realIdx === activeRecentIdx);
                    recentList.splice(realIdx, 1);
                    
                    if (recentList.length === 0) {
                        activeRecentIdx = -1;
                        hasActiveCanvas = false;
                        canvas.clear();
                        canvas.backgroundColor = 'transparent';
                        canvas.backgroundImage = null;
                        canvas.renderAll();
                        document.querySelectorAll('.btn-tool').forEach(btn => btn.classList.add('disabled'));
                        document.getElementById('sub_toolbar').style.display = 'none';
                        document.getElementById('edit_popup').style.display = 'none';
                    } else {
                        if (isDeletingActive) {
                            let nextIdx = Math.max(0, Math.min(activeRecentIdx, recentList.length - 1));
                            hasActiveCanvas = false; 
                            activeRecentIdx = -1; 
                            loadRecentItem(nextIdx);
                        } else if (realIdx < activeRecentIdx) {
                            activeRecentIdx--;
                        }
                    }
                    renderRecentList();
                };
                div.appendChild(delBtn);
                
                div.onmousedown = (e) => { if(e.button !== 0) return; loadRecentItem(realIdx); };
                
                container.appendChild(div);
            });
            
            // 활성 아이템 스크롤 중앙 정렬 기능 제거 (수동 스크롤만 사용)
        }

        function flushThumbDebounce() {
            if (window._thumbDebounce) {
                clearTimeout(window._thumbDebounce);
                window._thumbDebounce = null;
                if (activeRecentIdx >= 0) pushCurrentToRecent();
            }
        }

        // ── 썸네일 즉시 로드 (플래그/큐 방식 제거, 단순·고속) ─────────────
        let _recentLoadSeq = 0; // 최신 요청만 반영 (이전 요청 무시)

        function loadRecentItem(idx) {
            const item = recentList[idx];
            if (!item || idx === activeRecentIdx) return;
            flushThumbDebounce();
            
            prepareCanvasDisplay();

            // ★ 떠나기 전에 현재 캔버스 상태를 무조건 저장
            if (activeRecentIdx >= 0 && hasActiveCanvas) {
                pushCurrentToRecent();
            }

            activeRecentIdx = idx;
            renderRecentList();

            const seq = ++_recentLoadSeq;
            isHistoryAction = true;
            canvas.renderOnAddRemove = false;

            // ★ 고속 경로: 캐시된 배경 Image 객체가 있으면 경량 JSON 사용
            const useFastPath = item.bgImgCache && item.jsonLight;
            const jsonToLoad = useFastPath ? item.jsonLight : item.json;

            canvas.loadFromJSON(jsonToLoad, () => {
                if (seq !== _recentLoadSeq) return;

                canvas.renderOnAddRemove = true;
                const w = item.width || canvas.width;
                const h = item.height || canvas.height;
                canvas.setWidth(w);
                canvas.setHeight(h);

                function finishLoad() {
                    syncFabricContainerSize();
                    canvas.calcOffset();
                    enableTools();
                    applyFitZoom();
                    applyCanvasClipping();
                    canvas.renderAll();
                    initHistory();
                    isHistoryAction = false;
                }

                if (useFastPath) {
                    // 캐시된 Image 객체로 즉시 배경 복원 (Base64 디코딩 불필요)
                    const fabricBg = new fabric.Image(item.bgImgCache, {
                        originX: 'left', originY: 'top', left: 0, top: 0
                    });
                    canvas.setBackgroundImage(fabricBg, () => { finishLoad(); });
                } else {
                    finishLoad();
                }
            });
        }
        // 현재 활성 항목 인덱스
        let activeRecentIdx = -1;

        function updateCurrentThumbnail() {
            // no-op (호환성 유지)
        }

        function updateUndoRedoUI() {
            const undoBtn = document.getElementById('btn_undo');
            const redoBtn = document.getElementById('btn_redo');
            if (undoBtn) undoBtn.classList.toggle('disabled', historyIndex <= 0);
            if (redoBtn) redoBtn.classList.toggle('disabled', historyIndex >= stateHistory.length - 1);
            if (activeRecentIdx >= 0 && recentList[activeRecentIdx]) {
                recentList[activeRecentIdx].stateHistory = stateHistory;
                recentList[activeRecentIdx].historyIndex = historyIndex;
            }
            updateCurrentThumbnail();
        }

        function initHistory() {
            if (activeRecentIdx >= 0 && recentList[activeRecentIdx]) {
                const item = recentList[activeRecentIdx];
                if (item.stateHistory && item.stateHistory.length > 0) {
                    stateHistory = item.stateHistory;
                    historyIndex = item.historyIndex !== undefined ? item.historyIndex : item.stateHistory.length - 1;
                    updateUndoRedoUI();
                    return;
                }
            }

            const bgImg = canvas.backgroundImage;
            const bgColor = canvas.backgroundColor;
            canvas.backgroundImage = null;
            canvas.backgroundColor = null;
            const json = JSON.stringify(canvas);
            canvas.backgroundImage = bgImg;
            canvas.backgroundColor = bgColor;

            stateHistory = [{ objects: json, width: canvas.width, height: canvas.height }];
            historyIndex = 0;
            updateUndoRedoUI();
        }

        function saveHistory() {
            if (isHistoryAction || !hasActiveCanvas) return;
            
            // 성능 최적화: 수 MB의 배경 이미지를 제외하고 벡터 개체만 JSON으로 직렬화 (속도 10배 이상 향상)
            const bgImg = canvas.backgroundImage;
            const bgColor = canvas.backgroundColor;
            canvas.backgroundImage = null;
            canvas.backgroundColor = null;
            const json = JSON.stringify(canvas);
            canvas.backgroundImage = bgImg;
            canvas.backgroundColor = bgColor;
            
            if (stateHistory.length > 0 && stateHistory[historyIndex].objects === json) return;

            if (historyIndex < stateHistory.length - 1) { stateHistory = stateHistory.slice(0, historyIndex + 1); }
            
            stateHistory.push({ objects: json, width: canvas.width, height: canvas.height });
            
            historyIndex++;
            if (stateHistory.length > 50) { stateHistory.shift(); historyIndex--; }
            updateUndoRedoUI();
        }

        canvas.on('object:added', (e) => { 
            if (activeTool && activeTool !== 'crop' && activeTool !== 'eraser') {
                e.target.set('evented', false);
                e.target.set('selectable', false);
            }
            // 펜 브러시로 그린 선은 path:created에서 히스토리를 저장하므로 여기서 중복 저장 방지
            const isPenBrushPath = (activeTool === 'pen' && e.target.type === 'path' && !e.target.isTemp && canvas.isDrawingMode);
            if(!isHistoryAction && !e.target.isTemp && !isPenBrushPath) saveHistory();
            // ★ 개체 추가 시 Fabric 내부 래퍼 크기 동기화 (하단 깜빡임 방지)
            syncFabricContainerSize();
        });
        function normalizeScale(obj) {
            if (!obj || (obj.scaleX === 1 && obj.scaleY === 1)) return;
            const isArrow = (obj.type === 'group' && obj.getObjects().find(o => o.isArrowBody));
            const isPath = (obj.type === 'path' && !obj.isArrowBody);
            
            if (isArrow || isPath) {
                let oldBody = isArrow ? obj.getObjects().find(o => o.isArrowBody) : obj;
                let m = oldBody.calcTransformMatrix();
                let po = oldBody.pathOffset || { x: 0, y: 0 };
                
                let absPoints = [];
                oldBody.path.forEach(cmd => {
                    if(cmd[0] === 'M' || cmd[0] === 'L') absPoints.push(fabric.util.transformPoint({x: cmd[1] - po.x, y: cmd[2] - po.y}, m));
                    else if(cmd[0] === 'C') absPoints.push(fabric.util.transformPoint({x: cmd[5] - po.x, y: cmd[6] - po.y}, m));
                    else if(cmd[0] === 'Q') absPoints.push(fabric.util.transformPoint({x: cmd[3] - po.x, y: cmd[4] - po.y}, m));
                });
                
                let minX = Math.min(...absPoints.map(p=>p.x)), minY = Math.min(...absPoints.map(p=>p.y));
                
                let newPathStr = "";
                let finalP = null, prevP = null;
                oldBody.path.forEach(cmd => {
                    if(cmd[0] === 'M' || cmd[0] === 'L') {
                        let p = fabric.util.transformPoint({x: cmd[1] - po.x, y: cmd[2] - po.y}, m);
                        newPathStr += `${cmd[0]} ${p.x} ${p.y} `;
                        prevP = finalP; finalP = {x: p.x, y: p.y};
                    } else if(cmd[0] === 'C') {
                        let cp1 = fabric.util.transformPoint({x: cmd[1] - po.x, y: cmd[2] - po.y}, m);
                        let cp2 = fabric.util.transformPoint({x: cmd[3] - po.x, y: cmd[4] - po.y}, m);
                        let p = fabric.util.transformPoint({x: cmd[5] - po.x, y: cmd[6] - po.y}, m);
                        newPathStr += `${cmd[0]} ${cp1.x} ${cp1.y}, ${cp2.x} ${cp2.y}, ${p.x} ${p.y} `;
                        prevP = finalP; finalP = {x: p.x, y: p.y};
                    } else if(cmd[0] === 'Q') {
                        let cp1 = fabric.util.transformPoint({x: cmd[1] - po.x, y: cmd[2] - po.y}, m);
                        let p = fabric.util.transformPoint({x: cmd[3] - po.x, y: cmd[4] - po.y}, m);
                        newPathStr += `${cmd[0]} ${cp1.x} ${cp1.y}, ${p.x} ${p.y} `;
                        prevP = finalP; finalP = {x: p.x, y: p.y};
                    }
                });
                
                let size = oldBody.strokeWidth;
                let sColor = oldBody.stroke;
                let dashArr = oldBody.strokeDashArray;

                if (isArrow) {
                    let arrowType = oldBody.arrowType || obj.arrowType || sysArrowType;
                    let arrowSize = oldBody.arrowSize || obj.arrowSize || sysArrowSize;
                    let angle = Math.atan2(finalP.y - prevP.y, finalP.x - prevP.x);
                    let sizeMult = arrowSize === 'xs' ? 1.5 : arrowSize === 's' ? 2 : arrowSize === 'l' ? 4 : 3;
                    let w = size * sizeMult + 8;
                    let pullBack = (arrowType === 'stealth') ? w * 0.6 : (arrowType === 'open') ? 0 : w;
                    
                    let adjFinalX = finalP.x - Math.cos(angle) * pullBack;
                    let adjFinalY = finalP.y - Math.sin(angle) * pullBack;
                    
                    let parts = newPathStr.trim().split(' ');
                    parts[parts.length-2] = adjFinalX;
                    parts[parts.length-1] = adjFinalY;
                    newPathStr = parts.join(' ');
                    
                    let newBody = new fabric.Path(newPathStr, { fill: 'transparent', stroke: sColor, strokeWidth: size, strokeDashArray: dashArr, strokeLineCap: 'round', strokeLineJoin: 'round', isArrowBody: true, objectCaching: false, arrowType: arrowType, arrowSize: arrowSize });
                    let newHead = createArrowHead(finalP.x, finalP.y, angle, arrowType, arrowSize, sColor, size);
                    let newGroup = new fabric.Group([newBody, newHead], { selectable: true, arrowType: arrowType, arrowSize: arrowSize });
                    
                    canvas.remove(obj);
                    canvas.add(newGroup);
                    canvas.setActiveObject(newGroup);
                } else {
                    let newBody = new fabric.Path(newPathStr, { fill: 'transparent', stroke: sColor, strokeWidth: size, strokeDashArray: dashArr, strokeLineCap: 'round', strokeLineJoin: 'round', selectable: true, objectCaching: false });
                    canvas.remove(obj);
                    canvas.add(newBody);
                    canvas.setActiveObject(newBody);
                }
            }
        }

        canvas.on('object:modified', (e) => { 
            if(e.target && (e.target.scaleX !== 1 || e.target.scaleY !== 1)) {
                // Skip normalizeScale for shapes with linked text (rect/ellipse/polygon)
                // because normalizeScale recreates the object and breaks the linkedText binding
                const t = e.target;
                if (t.linkedText && ['rect', 'ellipse', 'polygon'].includes(t.type)) {
                    // Bake scale into width/height without recreating the object
                    if (t.type === 'rect') {
                        t.set({ width: t.width * t.scaleX, height: t.height * t.scaleY, scaleX: 1, scaleY: 1 });
                    } else if (t.type === 'ellipse') {
                        t.set({ rx: t.rx * t.scaleX, ry: t.ry * t.scaleY, scaleX: 1, scaleY: 1 });
                        t.set({ width: t.rx * 2, height: t.ry * 2 });
                    } else if (t.type === 'polygon') {
                        const sx = t.scaleX, sy = t.scaleY;
                        const newPoints = t.points.map(p => ({ x: p.x * sx, y: p.y * sy }));
                        t.set({ points: newPoints, scaleX: 1, scaleY: 1 });
                        t._calcDimensions();
                        t.setCoords();
                    }
                    // Update stored original dimensions for future clamping
                    t.originalWidth = t.width;
                    t.originalHeight = t.height;
                    t.originalScaleX = 1;
                    t.originalScaleY = 1;
                    t.setCoords();
                } else {
                    normalizeScale(e.target);
                }
            }
            if(!isHistoryAction) {
                saveHistory();
                // 썸네일 갱신 (디바운스 800ms)
                clearTimeout(window._thumbDebounce);
                window._thumbDebounce = setTimeout(() => {
                    if (activeRecentIdx >= 0) pushCurrentToRecent();
                }, 800);
            }
            syncFabricContainerSize();
        });
        canvas.on('object:removed', (e) => { 
            if(!isHistoryAction && !e.target.isTemp) {
                saveHistory();
                clearTimeout(window._thumbDebounce);
                window._thumbDebounce = setTimeout(() => {
                    if (activeRecentIdx >= 0) pushCurrentToRecent();
                }, 800);
            }
            syncFabricContainerSize();
        });

        function loadHistoryState(idx) {
            isHistoryAction = true;
            canvas.renderOnAddRemove = false;

            const state = stateHistory[idx];
            canvas.setWidth(state.width);
            canvas.setHeight(state.height);
            syncFabricContainerSize();
            
            const bgImg = canvas.backgroundImage;
            const bgColor = canvas.backgroundColor;

            canvas.loadFromJSON(state.objects, () => { 
                canvas.backgroundImage = bgImg;
                canvas.backgroundColor = bgColor;
                canvas.renderOnAddRemove = true; 
                syncFabricContainerSize();
                applyCanvasClipping(); 

                // ★ 핵심: setTimeout으로 새 macrotask에서 렌더링하여
                //    Chromium compositor가 프레임을 스케줄링할 기회를 확보
                setTimeout(() => {
                    canvas.renderAll(); 
                    isHistoryAction = false; 
                    updateUndoRedoUI(); 
                    updateGlobalCursor(); 
                }, 0);
            });
        }

        document.getElementById('btn_undo').addEventListener('click', () => {
            if (historyIndex <= 0 || !hasActiveCanvas) return;
            historyIndex--; loadHistoryState(historyIndex);
        });
        
        document.getElementById('btn_redo').addEventListener('click', () => {
            if (historyIndex >= stateHistory.length - 1 || !hasActiveCanvas) return;
            historyIndex++; loadHistoryState(historyIndex);
        });

        // ==========================================
        // 3. 도형 옵션 동적 전환 & 42색상 팔레트 연동 (형광색 및 오피스 색상 포함)
        // ==========================================
        const munsell35 = [
            {n:"검정",h:"#000000"},{n:"하양",h:"#FFFFFF"},{n:"투명",h:"transparent"},{n:"진회색",h:"#4A4A4A"},{n:"회색",h:"#7D7D7D"},{n:"갈색",h:"#8F4B28"},{n:"살구",h:"#F8C3CD"},
            {n:"빨강",h:"#E03C31"},{n:"주황빨강",h:"#E95513"},{n:"주황",h:"#F37121"},{n:"노랑주황",h:"#F9961B"},{n:"노랑",h:"#FFC408"},{n:"연두노랑",h:"#D1D22D"},{n:"연두",h:"#98CB4A"},
            {n:"초록연두",h:"#41B34E"},{n:"초록",h:"#009959"},{n:"청록초록",h:"#009E8E"},{n:"청록",h:"#00A1AE"},{n:"파랑청록",h:"#0087BA"},{n:"파랑",h:"#0068B7"},{n:"남색파랑",h:"#2B4B9B"},
            {n:"남색",h:"#3E318B"},{n:"보라남색",h:"#622D88"},{n:"보라",h:"#8E2382"},{n:"자주보라",h:"#B91B74"},{n:"자주",h:"#D61668"},{n:"빨강자주",h:"#E01D53"},{n:"연분홍",h:"#F4A7B9"},
            {n:"오피스 빨강",h:"#FF0000"},{n:"오피스 주황",h:"#FF6600"},{n:"오피스 노랑",h:"#FFFF00"},{n:"오피스 연두",h:"#00FF00"},{n:"오피스 청록",h:"#00FFFF"},{n:"오피스 파랑",h:"#0055FF"},{n:"오피스 보라",h:"#CC00FF"},
            {n:"형광노랑",h:"rgba(255, 255, 0, 0.6)"}, {n:"형광연두",h:"rgba(57, 255, 20, 0.6)"}, {n:"형광초록",h:"rgba(0, 255, 0, 0.6)"},
            {n:"형광하늘",h:"rgba(0, 255, 255, 0.6)"}, {n:"형광파랑",h:"rgba(0, 100, 255, 0.6)"}, {n:"형광분홍",h:"rgba(255, 20, 147, 0.6)"},
            {n:"형광빨강",h:"rgba(255, 50, 50, 0.6)"}
        ]; 
        const paletteEl = document.getElementById('color_palette');
        let targetColorBtn = null;
        let strokeColor = '#E03C31'; let fillColor = 'transparent'; let textColor = '#E03C31'; let textBg = 'transparent';
        let sysPenBallpointWeight = 3; let sysPenBallpointColor = '#E03C31';
        let sysPenHighlighterWeight = 20; let sysPenHighlighterColor = 'rgba(255, 255, 0, 0.3)';
        let penCurrentColor = sysPenBallpointColor;

        munsell35.forEach(c => { 
            const cell = document.createElement('div');
            cell.className = 'palette-cell'; cell.style.backgroundColor = c.h;
            cell.setAttribute('data-name', c.n); 
            if (c.h === 'transparent') cell.style.backgroundImage = 'linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc)';
            cell.addEventListener('mousedown', e => e.preventDefault());
            cell.addEventListener('click', () => { 
                const bgImg = c.h === 'transparent' ? cell.style.backgroundImage : 'none'; 
                if (targetColorBtn === 'stroke' || targetColorBtn === 'edit_shape_stroke' || targetColorBtn === 'edit_line_stroke' || targetColorBtn === 'set_shape_stroke') { 
                    const elId = targetColorBtn === 'stroke' ? 'btn_stroke_color' : targetColorBtn === 'set_shape_stroke' ? 'set_shape_stroke_color' : targetColorBtn;
                    document.getElementById(elId).style.backgroundColor = c.h; 
                    if(targetColorBtn === 'stroke' || targetColorBtn === 'set_shape_stroke') strokeColor = c.h; 
                } else if (targetColorBtn === 'fill' || targetColorBtn === 'edit_shape_fill' || targetColorBtn === 'edit_line_fill' || targetColorBtn === 'set_shape_fill') {
                    const elId = targetColorBtn === 'fill' ? 'btn_fill_color' : targetColorBtn === 'set_shape_fill' ? 'set_shape_fill_color' : targetColorBtn;
                    document.getElementById(elId).style.backgroundColor = c.h;
                    document.getElementById(elId).style.backgroundImage = bgImg; 
                    if(targetColorBtn === 'fill' || targetColorBtn === 'set_shape_fill') fillColor = c.h; 
                } else if (targetColorBtn === 'text' || targetColorBtn === 'text_bg' || targetColorBtn === 'set_text' || targetColorBtn === 'set_text_bg' || targetColorBtn === 'edit_text_c' || targetColorBtn === 'edit_text_b') { 
                    const elId = targetColorBtn === 'text' ? 'btn_text_color' : targetColorBtn === 'text_bg' ? 'btn_text_bg' : targetColorBtn === 'set_text' ? 'set_txt_color' : targetColorBtn === 'set_text_bg' ? 'set_txt_bg_color' : targetColorBtn === 'edit_text_c' ? 'edit_text_color' : 'edit_text_bg';
                    document.getElementById(elId).style.backgroundColor = c.h;
                    document.getElementById(elId).style.backgroundImage = bgImg;
                    if(targetColorBtn === 'text' || targetColorBtn === 'set_text') textColor = c.h; else if(targetColorBtn === 'text_bg' || targetColorBtn === 'set_text_bg') textBg = c.h; 
                } else if (targetColorBtn === 'new_bg') {
                    document.getElementById('new_bg_color').style.backgroundColor = c.h; 
                } else if (targetColorBtn === 'pen' || targetColorBtn === 'set_pen_ballpoint' || targetColorBtn === 'set_pen_highlighter') {
                    const elId = targetColorBtn === 'pen' ? 'btn_pen_color' : targetColorBtn === 'set_pen_ballpoint' ? 'set_pen_ballpoint_color' : 'set_pen_highlighter_color';
                    let finalColor = c.h;
                    if (targetColorBtn === 'set_pen_highlighter' || (targetColorBtn === 'pen' && document.getElementById('pen_type').value === 'highlighter')) {
                        let opacity = parseInt(document.getElementById('set_pen_highlighter_opacity').value) || 30;
                        finalColor = new fabric.Color(c.h).setAlpha(opacity / 100).toRgba();
                    }
                    document.getElementById(elId).style.backgroundColor = finalColor;
                    if(targetColorBtn === 'pen') {
                        penCurrentColor = finalColor;
                        if(document.getElementById('pen_type').value === 'ballpoint') sysPenBallpointColor = finalColor;
                        else sysPenHighlighterColor = finalColor;
                        updatePenBrush();
                    }
                }
                paletteEl.style.display = 'none'; 
                if (['text', 'set_text', 'edit_text_c'].includes(targetColorBtn)) {
                    updateActiveText('fill', c.h);
                } else if (['text_bg', 'set_text_bg', 'edit_text_b'].includes(targetColorBtn)) {
                    updateActiveText('backgroundColor', getTextBgOpacity());
                }
                if(targetColorBtn === 'pen' && document.querySelector('input[name="pen_mode"]:checked').value === 'straight') {
                    // Update stroke color for straight line mode
                }
            }); 
            paletteEl.appendChild(cell); 
        });

        // 바탕 클릭 시 팔레트 닫기
        document.addEventListener('mousedown', e => { 
            if (!e.target.closest('#color_palette') && !e.target.closest('.color-btn')) paletteEl.style.display = 'none'; 
            if (!e.target.closest('#canvas_context_menu')) {
                const ctxMenu = document.getElementById('canvas_context_menu');
                if(ctxMenu) ctxMenu.style.display = 'none';
            }
        });

        // 우클릭 방지 및 캔버스 컨텍스트 메뉴
        document.addEventListener('contextmenu', function(e) {
            if (e.target.closest('#toolbar') || e.target.closest('#sidebar') || e.target.closest('#sub_toolbar')) {
                e.preventDefault();
                return;
            }
            if (e.target.closest('.canvas-container')) {
                e.preventDefault();
                if(!hasActiveCanvas) return;
                
                const ctxMenu = document.getElementById('canvas_context_menu');
                let pointer = canvas.getPointer(e);
                let target = canvas.findTarget(e, false);
                
                lastCanvasClick = { x: pointer.x, y: pointer.y };
                ctxMenu.innerHTML = '';
                
                if (target) {
                    canvas.setActiveObject(target);
                    canvas.requestRenderAll();
                    
                    ctxMenu.innerHTML = `
                        <div class="menu-item" id="ctx_edit"><span>수정하기</span></div>
                        <div class="menu-divider"></div>
                        <div class="menu-item" id="ctx_cut"><span>잘라내기</span><span class="menu-shortcut">Ctrl+X</span></div>
                        <div class="menu-item" id="ctx_copy"><span>복사하기</span><span class="menu-shortcut">Ctrl+C</span></div>
                        <div class="menu-item" id="ctx_del"><span>삭제하기</span><span class="menu-shortcut">Del</span></div>
                    `;
                    
                    document.getElementById('ctx_edit').onclick = () => { ctxMenu.style.display = 'none'; canvas.fire('mouse:dblclick', { target: target, e: e }); };
                    document.getElementById('ctx_cut').onclick = () => { ctxMenu.style.display = 'none'; window.dispatchEvent(new KeyboardEvent('keydown', { key: 'x', ctrlKey: true })); };
                    document.getElementById('ctx_copy').onclick = () => { ctxMenu.style.display = 'none'; window.dispatchEvent(new KeyboardEvent('keydown', { key: 'c', ctrlKey: true })); };
                    document.getElementById('ctx_del').onclick = () => { ctxMenu.style.display = 'none'; window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete' })); };
                } else {
                    canvas.discardActiveObject();
                    canvas.requestRenderAll();
                    
                    const canUndo = !document.getElementById('btn_undo').classList.contains('disabled');
                    const canRedo = !document.getElementById('btn_redo').classList.contains('disabled');
                    const canCopy = !document.getElementById('btn_action_copy').classList.contains('disabled');
                    const canPaste = !!myClipboard;
                    
                    ctxMenu.innerHTML = `
                        <div class="menu-item ${canUndo ? '' : 'disabled'}" id="ctx_undo"><span>뒤로</span></div>
                        <div class="menu-item ${canRedo ? '' : 'disabled'}" id="ctx_redo"><span>앞으로</span></div>
                        <div class="menu-divider"></div>
                        <div class="menu-item ${canCopy ? '' : 'disabled'}" id="ctx_copy_img"><span>복사하기</span></div>
                        <div class="menu-item ${canPaste ? '' : 'disabled'}" id="ctx_paste"><span>붙여넣기</span><span class="menu-shortcut">Ctrl+V</span></div>
                    `;
                    
                    document.getElementById('ctx_undo').onclick = () => { ctxMenu.style.display = 'none'; document.getElementById('btn_undo').click(); };
                    document.getElementById('ctx_redo').onclick = () => { ctxMenu.style.display = 'none'; document.getElementById('btn_redo').click(); };
                    document.getElementById('ctx_copy_img').onclick = () => { ctxMenu.style.display = 'none'; document.getElementById('btn_action_copy').click(); };
                    document.getElementById('ctx_paste').onclick = () => { ctxMenu.style.display = 'none'; window.dispatchEvent(new KeyboardEvent('keydown', { key: 'v', ctrlKey: true })); };
                }
                
                ctxMenu.style.display = 'block';
                let x = e.clientX;
                let y = e.clientY;
                if (x + ctxMenu.offsetWidth > window.innerWidth) x -= ctxMenu.offsetWidth;
                if (y + ctxMenu.offsetHeight > window.innerHeight) y -= ctxMenu.offsetHeight;
                ctxMenu.style.left = x + 'px';
                ctxMenu.style.top = y + 'px';
            }
        });

        function bindCP(id, t) {
            const el = document.getElementById(id);
            if(el) {
                el.addEventListener('click', e => { 
                    targetColorBtn = t; paletteEl.style.display = 'grid'; 
                    paletteEl.style.left = e.pageX + 'px'; paletteEl.style.top = (e.pageY + 20) + 'px'; 
                });
            }
        }
        
        bindCP('btn_stroke_color', 'stroke'); bindCP('btn_fill_color', 'fill');
        document.getElementById('btn_text_color').addEventListener('mousedown', e => e.preventDefault());
        document.getElementById('btn_text_bg').addEventListener('mousedown', e => e.preventDefault());
        bindCP('btn_text_color', 'text'); bindCP('btn_text_bg', 'text_bg');
        bindCP('new_bg_color', 'new_bg');
        bindCP('btn_pen_color', 'pen');
        bindCP('set_pen_ballpoint_color', 'set_pen_ballpoint'); bindCP('set_pen_highlighter_color', 'set_pen_highlighter');
        bindCP('edit_shape_stroke', 'edit_shape_stroke'); bindCP('edit_shape_fill', 'edit_shape_fill'); 
        bindCP('edit_line_stroke', 'edit_line_stroke'); bindCP('edit_line_fill', 'edit_line_fill'); 
        bindCP('edit_text_color', 'edit_text_c'); bindCP('edit_text_bg', 'edit_text_b'); 
        bindCP('set_shape_stroke_color', 'set_shape_stroke'); bindCP('set_shape_fill_color', 'set_shape_fill');
        bindCP('set_txt_color', 'set_text'); bindCP('set_txt_bg_color', 'set_text_bg');

        function updateShapeOptions() {
            const type = document.getElementById('shape_type').value;
            const container = document.getElementById('shape_options_container');
            const isLineShape = ['line', 'arrow'].includes(type);
            
            document.getElementById('btn_fill_color').style.display = isLineShape ? 'none' : 'inline-block';
            document.getElementById('label_fill_color').style.display = isLineShape ? 'none' : 'inline-block';

            if (['rect', 'ellipse', 'rhombus'].includes(type)) {
                container.innerHTML = '<label><input type="checkbox" id="chk_dashed"> 점선</label>';
            } else {
                container.innerHTML = '<label><input type="checkbox" id="chk_dashed"> 점선</label>' +
                                      '<label><input type="radio" name="line_type" value="normal" checked> 일반</label>' +
                                      '<label><input type="radio" name="line_type" value="poly"> 꺾은 선</label>' +
                                      '<label><input type="radio" name="line_type" value="curve"> 곡선</label>';
            }
        }
        document.getElementById('shape_type').addEventListener('change', updateShapeOptions);
        updateShapeOptions();

        let activeTool = null; let isDrawing = false; let origX, origY;
        let currentShape = null; let liveEmojiImgObj = null; let arrowHead = null;
        let selectedEmoji = '😀'; let selectedEmojiUrl = null; let uploadedImageSrc = null;
        let customEmojiFolders = [];
        let txtB = false, txtI = false, txtU = false; let editingObject = null;
        let origShapeRatio = 1, origImageRatio = 1, origLineRatio = 1;
        
        let sysShapeOpacity = 0.2; let sysEraserFat = 1.5; let sysArrowType = 'triangle'; let sysArrowSize = 'm';

        function collectSettings() {
            const settingsIds = [
                'set_theme', 'set_cap_w', 'set_cap_h', 'set_cap_quality',
                'set_txt_size', 'set_txt_b_chk', 'set_txt_i_chk', 'set_txt_u_chk', 'set_text_align',
                'set_txt_bg_opacity', 'set_pen_ballpoint_weight',
                'set_pen_highlighter_weight', 'set_pen_highlighter_opacity',
                'set_shape_weight', 'set_shape_opacity_val', 'set_arrow_type', 'set_arrow_size',
                'set_eraser_fat', 'set_mosaic_px', 'setting_save_format', 'set_recent_max', 'set_recent_max_action'
            ];
            const colorIds = [
                'set_txt_color', 'set_txt_bg_color', 'set_pen_ballpoint_color',
                'set_pen_highlighter_color', 'set_shape_stroke_color', 'set_shape_fill_color'
            ];
            let data = {};
            settingsIds.forEach(id => {
                let el = document.getElementById(id);
                if(el) {
                    if(el.type === 'checkbox') data[id] = el.checked;
                    else data[id] = el.value;
                }
            });
            colorIds.forEach(id => {
                let el = document.getElementById(id);
                if(el) {
                    data[id] = { bg: el.style.backgroundColor, img: el.style.backgroundImage };
                }
            });
            data.customEmojiFolders = customEmojiFolders;
            return data;
        }

        window.restoreSettings = function(jsonStr) {
            try {
                let data = JSON.parse(jsonStr);
                if (data.customEmojiFolders) {
                    customEmojiFolders = data.customEmojiFolders;
                }
                for(let id in data) {
                    let el = document.getElementById(id);
                    if(!el) continue;
                    if(data[id] && data[id].bg !== undefined) {
                        el.style.backgroundColor = data[id].bg;
                        el.style.backgroundImage = data[id].img;
                    } else if(el.type === 'checkbox') {
                        el.checked = data[id];
                    } else {
                        el.value = data[id];
                        let group = document.getElementById(id + '_group');
                        if(group) {
                            group.querySelectorAll('button').forEach(b => {
                                if(b.getAttribute('data-val') === String(data[id])) b.classList.add('active');
                                else b.classList.remove('active');
                            });
                        }
                    }
                }
                applySettings();
            } catch(e) {}
        };

        window.applySettings = function() {
            renderEmojiFolderList();
            loadCustomEmojisFromFolders();
            if(document.getElementById('text_size_input') && document.getElementById('set_txt_size')) {
                document.getElementById('text_size_input').value = document.getElementById('set_txt_size').value;
            }
            if(document.getElementById('text_align') && document.getElementById('set_text_align')) {
                const alignVal = document.getElementById('set_text_align').value || 'center';
                document.getElementById('text_align').value = alignVal;
                document.querySelectorAll('#text_align_group .btn-align').forEach(b => b.classList.remove('active'));
                const targetBtn = document.querySelector(`#text_align_group .btn-align[data-align="${alignVal}"]`);
                if(targetBtn) targetBtn.classList.add('active');
            }
            txtB = document.getElementById('set_txt_b_chk')?.checked || false;
            txtI = document.getElementById('set_txt_i_chk')?.checked || false;
            txtU = document.getElementById('set_txt_u_chk')?.checked || false;
            if(txtB) document.getElementById('btn_txt_b')?.classList.add('active'); else document.getElementById('btn_txt_b')?.classList.remove('active');
            if(txtI) document.getElementById('btn_txt_i')?.classList.add('active'); else document.getElementById('btn_txt_i')?.classList.remove('active');
            if(txtU) document.getElementById('btn_txt_u')?.classList.add('active'); else document.getElementById('btn_txt_u')?.classList.remove('active');

            sysPenBallpointWeight = parseInt(document.getElementById('set_pen_ballpoint_weight')?.value || 3);
            sysPenBallpointColor = document.getElementById('set_pen_ballpoint_color')?.style.backgroundColor || '#E03C31';
            sysPenHighlighterWeight = parseInt(document.getElementById('set_pen_highlighter_weight')?.value || 10);
            sysPenHighlighterColor = document.getElementById('set_pen_highlighter_color')?.style.backgroundColor || 'rgba(255, 255, 0, 0.3)';
            
            if (document.getElementById('pen_type')?.value === 'ballpoint') {
                if(document.getElementById('pen_weight')) document.getElementById('pen_weight').value = sysPenBallpointWeight;
                if(document.getElementById('btn_pen_color')) document.getElementById('btn_pen_color').style.backgroundColor = sysPenBallpointColor;
                penCurrentColor = sysPenBallpointColor;
            } else {
                if(document.getElementById('pen_weight')) document.getElementById('pen_weight').value = sysPenHighlighterWeight;
                if(document.getElementById('btn_pen_color')) document.getElementById('btn_pen_color').style.backgroundColor = sysPenHighlighterColor;
                penCurrentColor = sysPenHighlighterColor;
            }
            updatePenBrush();

            if(document.getElementById('shape_weight') && document.getElementById('set_shape_weight')) {
                document.getElementById('shape_weight').value = document.getElementById('set_shape_weight').value;
            }
            sysShapeOpacity = (parseFloat(document.getElementById('set_shape_opacity_val')?.value) || 20) / 100;
            sysArrowType = document.getElementById('set_arrow_type')?.value || 'triangle';
            sysArrowSize = document.getElementById('set_arrow_size')?.value || 'm';
            sysEraserFat = parseFloat(document.getElementById('set_eraser_fat')?.value) || 1.5;
            
            window.sysMosaicPx = parseInt(document.getElementById('set_mosaic_px')?.value) || 5;
            
            strokeColor = document.getElementById('set_shape_stroke_color')?.style.backgroundColor || '#E03C31';
            if(document.getElementById('btn_stroke_color')) document.getElementById('btn_stroke_color').style.backgroundColor = strokeColor;
            
            textColor = document.getElementById('set_txt_color')?.style.backgroundColor || '#E03C31';
            if(document.getElementById('btn_text_color')) document.getElementById('btn_text_color').style.backgroundColor = textColor;

            fillColor = document.getElementById('set_shape_fill_color')?.style.backgroundColor || 'transparent';
            if(document.getElementById('btn_fill_color')) {
                document.getElementById('btn_fill_color').style.backgroundColor = fillColor;
                document.getElementById('btn_fill_color').style.backgroundImage = document.getElementById('set_shape_fill_color')?.style.backgroundImage || '';
            }

            updateEraserCursor();

            // ── 테마 적용 ────────────────────────────────────────────
            applyTheme(document.getElementById('set_theme').value);

            // 백엔드에 설정 저장
            if (window.pyBackend) {
                window.pyBackend.save_settings(JSON.stringify(collectSettings()));
            }
        }

        window.addEmojiFolder = async function() {
            if (customEmojiFolders.length >= 5) {
                return customAlert("사용자 정의 폴더는 최대 5개까지만 추가할 수 있습니다.");
            }
            if (typeof pyBackend !== 'undefined') {
                const folder = await pyBackend.select_directory();
                if (folder) {
                    if (customEmojiFolders.includes(folder)) return customAlert("이미 추가된 폴더입니다.");
                    customEmojiFolders.push(folder);
                    renderEmojiFolderList();
                    if (window.pyBackend) window.pyBackend.save_settings(JSON.stringify(collectSettings()));
                }
            }
        };

        window.removeEmojiFolder = function(index) {
            customEmojiFolders.splice(index, 1);
            renderEmojiFolderList();
            if (window.pyBackend) window.pyBackend.save_settings(JSON.stringify(collectSettings()));
        };

        window.renderEmojiFolderList = function() {
            const listEl = document.getElementById('emoji_folder_list');
            if (!listEl) return;
            listEl.innerHTML = '';
            customEmojiFolders.forEach((folder, idx) => {
                const div = document.createElement('div');
                div.style.display = 'flex'; div.style.justifyContent = 'space-between'; div.style.background = '#f8fafc'; div.style.padding = '4px 8px'; div.style.borderRadius = '4px'; div.style.alignItems = 'center';
                div.innerHTML = `<span style="font-size:11px; color:#334155; word-break:break-all;">${folder}</span><button onclick="removeEmojiFolder(${idx})" style="color:red; background:none; border:none; cursor:pointer; font-weight:bold;">X</button>`;
                listEl.appendChild(div);
            });
        };

        window.loadCustomEmojisFromFolders = async function() {
            if (typeof pyBackend === 'undefined') return;
            let allCustomEmojis = [];
            let customIcons = {};
            for (let i = 0; i < customEmojiFolders.length; i++) {
                const folder = customEmojiFolders[i];
                try {
                    const jsonStr = await pyBackend.get_images_in_directory(folder);
                    const images = JSON.parse(jsonStr);
                    allCustomEmojis = allCustomEmojis.concat(images);
                    
                    const categoryName = folder.split('\\').pop().split('/').pop();
                    const num = i + 1;
                    const svgStr = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#3b82f6"/><text x="12" y="16" fill="white" font-size="12" font-family="Arial" font-weight="bold" text-anchor="middle">${num}</text></svg>`;
                    customIcons[categoryName] = svgStr;
                } catch (e) {
                    console.error("Failed to load emoji folder", folder, e);
                }
            }
            const picker = document.querySelector('emoji-picker');
            if (picker) {
                picker.customEmoji = allCustomEmojis;
                picker.customCategoryIcons = customIcons;
            }
        };

        function applyTheme(mode) {
            if (mode === 'dark') {
                document.body.classList.add('dark-mode');
            } else if (mode === 'light') {
                document.body.classList.remove('dark-mode');
            } else {
                // 시스템 설정 따르기
                if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                    document.body.classList.add('dark-mode');
                } else {
                    document.body.classList.remove('dark-mode');
                }
            }
        }

        // 페이지 로드 시 시스템 테마 자동 감지
        applyTheme('system');
        // 시스템 테마 변경 실시간 감지
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
                if (document.getElementById('set_theme').value === 'system') applyTheme('system');
            });
        }


        function getFillOpacity() {
            if(fillColor === 'transparent') return 'rgba(0,0,0,0)';
            return new fabric.Color(fillColor).setAlpha(sysShapeOpacity).toRgba();
        }

        function getTextBgOpacity() {
            let o = parseInt(document.getElementById('set_txt_bg_opacity').value) / 100;
            if(textBg === 'transparent') return 'rgba(0,0,0,0)';
            if(textBg.startsWith('rgba')) return textBg;
            return new fabric.Color(textBg).setAlpha(o).toRgba();
        }

        function updateObjectSelectability() {
            const isDrawingTool = activeTool && activeTool !== 'crop' && activeTool !== 'eraser';
            const isCropTool    = activeTool === 'crop';
            
            canvas.getObjects().forEach(obj => {
                if (obj.isTemp) return;  // 임시 개체는 건드리지 않음
                if (isDrawingTool || isCropTool) {
                    obj.set({ evented: false, selectable: false });
                } else if (activeTool === 'eraser') {
                    obj.set({ evented: true, selectable: false });
                } else {
                    obj.set({
                        evented: true,
                        selectable: true,
                        hoverCursor: (obj.type === 'i-text' || obj.type === 'text' || obj.type === 'textbox') ? 'text' : 'move'
                    });
                }
            });
            canvas.selection = !isDrawingTool && !isCropTool;
        }

        const customEraserCursor = document.getElementById('custom_eraser_cursor');
        
        let isEraserFatState = false; // 글로벌 DOM 연속 조작 방지 상태
        
        
        function deactivateActiveTool() {
            const activeBtn = document.querySelector('.btn-tool.group-edit.active');
            if (activeBtn) {
                const pin = activeBtn.querySelector('.pin-icon');
                if (pin && pin.classList.contains('active')) return;
                activeBtn.click(); // This toggles it off
            }
        }

        function updateGlobalCursor() {
            if (activeTool === 'text') {
                workspace.style.cursor = 'text';
                canvas.defaultCursor = 'text';
                customEraserCursor.style.display = 'none';
            } else if (activeTool === 'eraser') {
                workspace.style.cursor = 'none';
                canvas.defaultCursor = 'none';
                customEraserCursor.style.display = 'flex';
                updateEraserCursor(); 
                isEraserFatState = false; // 툴 전환 시 지우개 상태 동기화
            } else if (activeTool) {
                workspace.style.cursor = 'crosshair';
                canvas.defaultCursor = 'crosshair';
                customEraserCursor.style.display = 'none';
            } else {
                workspace.style.cursor = 'grab';
                canvas.defaultCursor = 'default';
                customEraserCursor.style.display = 'none';
            }
            updateObjectSelectability();
        }

        function updateEraserCursor(isFat = false) {
            const normalSize = 32;
            const fatSize = 32 * sysEraserFat;
            const size = isFat ? fatSize : normalSize;
            
            customEraserCursor.style.width = size + 'px';
            customEraserCursor.style.height = size + 'px';
        }
        
        window.addEventListener('mousemove', e => {
            if (activeTool === 'eraser') {
                customEraserCursor.style.transform = `translate(${e.clientX}px, ${e.clientY}px) translate(-50%, -50%)`;
            }
        });

        function enableTools() {
            hasActiveCanvas = true; 
            document.querySelectorAll('.btn-tool.disabled').forEach(btn => btn.classList.remove('disabled'));
            applyCanvasClipping();
            updateGlobalCursor();
        }

        function updateSubToolbarPosition(btn) {
            const sub = document.getElementById('sub_toolbar');
            if(sub.style.display === 'block') {
                const rect = btn.getBoundingClientRect();
                sub.style.top = (rect.bottom + 10) + 'px'; sub.style.left = (rect.left + rect.width / 2) + 'px';
            }
        }

        const toolbar = document.getElementById('toolbar');
        // 상단 툴바가 상단 고정으로 변경되어 드래그 기능을 제거합니다.

        // ==========================================
        // 4. 파이썬 백엔드 캡처 연동
        // ==========================================
        let pyBackend = null;
        let historySaveTimer = null;
        function triggerHistorySave() {
            clearTimeout(historySaveTimer);
            historySaveTimer = setTimeout(() => {
                if (pyBackend) {
                    // bgImgCache(HTMLImageElement)와 jsonLight는 직렬화 불가 → 제외
                    const cleanList = recentList.map(item => ({
                        thumb: item.thumb,
                        json: item.json,
                        bgSrc: item.bgSrc,
                        bgColor: item.bgColor,
                        width: item.width,
                        height: item.height,
                        time: item.time
                    }));
                    pyBackend.save_history(JSON.stringify(cleanList));
                }
            }, 1000);
        }
        
        window.addEventListener('load', () => {
            if (typeof QWebChannel !== 'undefined') {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    pyBackend = channel.objects.pyBackend;
                    window.pyBackend = channel.objects.pyBackend;
                    
                    if (pyBackend) {
                        pyBackend.load_settings((settingsStr) => {
                            if (settingsStr) restoreSettings(settingsStr);
                        });
                        
                        pyBackend.load_history((historyStr) => {
                            if (historyStr) {
                                try {
                                    const parsed = JSON.parse(historyStr);
                                    if (Array.isArray(parsed) && parsed.length > 0) {
                                        recentList = parsed;
                                        renderRecentList();
                                        loadRecentItem(0);
                                        
                                        // ★ 백그라운드에서 bgImgCache/jsonLight 복원 (고속 전환 준비)
                                        setTimeout(() => {
                                            recentList.forEach(item => {
                                                if (!item.bgImgCache && item.json) {
                                                    try {
                                                        const p = JSON.parse(item.json);
                                                        if (p.backgroundImage && p.backgroundImage.src) {
                                                            const img = new Image();
                                                            img.src = p.backgroundImage.src;
                                                            item.bgImgCache = img;
                                                            delete p.backgroundImage;
                                                            item.jsonLight = JSON.stringify(p);
                                                        }
                                                    } catch(e2) {}
                                                }
                                            });
                                        }, 500);
                                    }
                                } catch(e) {}
                            }
                        });
                    }
                });
            }
        });

        const captureOverlay = document.getElementById('capture_overlay');
        const guideX = document.getElementById('guide_x'); const guideY = document.getElementById('guide_y');
        const selectionBox = document.getElementById('selection_box');
        let isCaptureMode = false;

        const grpCapture = document.getElementById('grp_capture'); const dropdownCapture = document.getElementById('dropdown_capture');
        grpCapture.addEventListener('mouseenter', () => dropdownCapture.style.display = 'block');
        grpCapture.addEventListener('mouseleave', () => dropdownCapture.style.display = 'none');

        document.querySelectorAll('#dropdown_capture button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const currentCapMode = e.target.getAttribute('data-mode'); 
                dropdownCapture.style.display = 'none';
                
                if (pyBackend) {
                    // Python으로 캡처 명령 전송
                    const capQuality = document.getElementById('set_cap_quality')?.value || 'normal';
                    if (currentCapMode === 'size') {
                        const w = document.getElementById('set_cap_w')?.value || 800;
                        const h = document.getElementById('set_cap_h')?.value || 600;
                        pyBackend.start_capture(`size_${w}_${h}`, capQuality);
                    } else {
                        pyBackend.start_capture(currentCapMode, capQuality);
                    }
                } else {
                    showToast("파이썬 백엔드가 연결되지 않았습니다.");
                }
            });
        });
        document.getElementById('btn_new_capture').addEventListener('click', () => document.querySelector('#dropdown_capture button[data-mode="manual"]').click());

        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (document.querySelectorAll('.modal[style*="display: block"]').length > 0) { closeModals(); closeDialog(); return; }
                if(multiClickDrawing) { finalizeMultiClickDrawing(); return; } 
                if (activeTool) document.querySelectorAll('.btn-tool.group-edit.active').forEach(btn => btn.click());
            }
        });

        window.receiveCapturedImage = function(base64Data) {
            if (base64Data) {
                isHistoryAction = true;
                fabric.Image.fromURL("data:image/webp;base64," + base64Data, (img) => {
                    pushCurrentToRecent(); // 이전 작업 보존
                    activeRecentIdx = -1; // 새 항목 추가를 위해 인덱스 리셋
                    stateHistory = []; historyIndex = -1;
                    canvas.clear(); 
                    img.set({ originX: 'left', originY: 'top', left: 0, top: 0, scaleX: 1, scaleY: 1 });
                    commitLoadToCanvas(img, img.width, img.height, null);
                    // commitLoadToCanvas -> finalizeLoad -> saveHistory -> pushCurrentToRecent 자동 호출됨
                });
                    document.getElementById('btn_tool_shape').click();
                    const rectBtn = document.querySelector('#shape_type_group button[data-val="rect"]');
                    if (rectBtn) rectBtn.click();
            }
        };


        // ==========================================
        // 5. 파일 열기, 저장, 복사, 인쇄
        // ==========================================
        const grpSave = document.getElementById('grp_save'); const dropdownSave = document.getElementById('dropdown_save');
        grpSave.addEventListener('mouseenter', () => { if(hasActiveCanvas) dropdownSave.style.display = 'block'; });
        grpSave.addEventListener('mouseleave', () => dropdownSave.style.display = 'none');

        document.getElementById('btn_action_open').addEventListener('click', () => document.getElementById('file_open_input').click());
        document.getElementById('file_open_input').addEventListener('change', e => {
            const file = e.target.files[0]; if (!file) return;
            const reader = new FileReader();
            if(file.name.endsWith('.json')) {
                reader.onload = f => {
                    prepareCanvasDisplay();
                    isHistoryAction = true; pushCurrentToRecent();
                    activeRecentIdx = -1;
                    stateHistory = []; historyIndex = -1;
                    
                    canvas.loadFromJSON(f.target.result, () => {
                        let parsed = {};
                        try { parsed = JSON.parse(f.target.result); } catch(e) {}
                        
                        let baseW = parsed.width || (canvas.backgroundImage ? canvas.backgroundImage.width * canvas.backgroundImage.scaleX : canvas.width);
                        let baseH = parsed.height || (canvas.backgroundImage ? canvas.backgroundImage.height * canvas.backgroundImage.scaleY : canvas.height);
                        if (parsed.backgroundColor) canvas.backgroundColor = parsed.backgroundColor;

                        canvas.setWidth(baseW); canvas.setHeight(baseH); 
                        syncFabricContainerSize();
                        canvas.calcOffset();
                        
                        enableTools(); applyFitZoom(); applyCanvasClipping(); 
                        canvas.renderAll(); initHistory(); isHistoryAction = false;
                        pushCurrentToRecent();
                        renderRecentList();
                    });
                }; reader.readAsText(file);
            } else {
                reader.onload = f => fabric.Image.fromURL(f.target.result, img => {
                    isHistoryAction = true;
                    pushCurrentToRecent();  // 이전 항목 보존 (새 항목으로 전환 전)
                    activeRecentIdx = -1;   // 새 캔버스 로드 → 인덱스 초기화
                    stateHistory = []; historyIndex = -1;
                    const naturalW = img.naturalWidth  || img.width;
                    const naturalH = img.naturalHeight || img.height;

                    img.set({
                        scaleX: 1, scaleY: 1,
                        originX: 'left', originY: 'top',
                        left: 0, top: 0
                    });
                    canvas.clear();
                    commitLoadToCanvas(img, naturalW, naturalH, null);
                }); reader.readAsDataURL(file);
            }
        });

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg; toast.style.opacity = '1'; toast.style.pointerEvents = 'auto';
            setTimeout(() => { toast.style.opacity = '0'; toast.style.pointerEvents = 'none'; }, 2000);
        }

        function getSaveBlobAndName(format) {
            canvas.discardActiveObject();
            let oldClip = canvas.clipPath; canvas.clipPath = null; canvas.renderAll();
            
            const dateStr = new Date().toISOString().replace(/T/, '_').replace(/:/g, '').split('.')[0];
            const baseName = `Capcraft_${dateStr}`;
            
            let blob, suggestedName, mime;
            
            if (format === 'json') {
                const jsonStr = JSON.stringify(canvas.toJSON(['width', 'height', 'backgroundColor']));
                blob = new Blob([jsonStr], {type: "application/json"});
                suggestedName = `${baseName}.json`;
                mime = 'application/json';
            } else if (format === 'pdf') {
                const dataUrl = canvas.toDataURL({ format: 'png', quality: 1, multiplier: 1, left: 0, top: 0, width: canvas.width, height: canvas.height });
                const { jsPDF } = window.jspdf;
                const pdf = new jsPDF({ orientation: canvas.width > canvas.height ? 'l' : 'p', unit: 'px', format: [canvas.width, canvas.height] });
                pdf.addImage(dataUrl, 'PNG', 0, 0, canvas.width, canvas.height);
                blob = pdf.output('blob');
                suggestedName = `${baseName}.pdf`;
                mime = 'application/pdf';
            } else {
                const f = format === 'jpg' ? 'jpeg' : 'png';
                const dataUrl = canvas.toDataURL({ format: f, quality: 1, multiplier: 1, left: 0, top: 0, width: canvas.width, height: canvas.height });
                const byteString = atob(dataUrl.split(',')[1]);
                const ab = new ArrayBuffer(byteString.length);
                const ia = new Uint8Array(ab);
                for (let i = 0; i < byteString.length; i++) ia[i] = byteString.charCodeAt(i);
                blob = new Blob([ab], {type: `image/${f}`});
                suggestedName = `${baseName}.${format}`;
                mime = `image/${f}`;
            }
            
            canvas.clipPath = oldClip; canvas.renderAll();
            return { blob, suggestedName, mime };
        }

        async function performSave(format) {
            if(!hasActiveCanvas) return;
            dropdownSave.style.display = 'none';
            const { blob, suggestedName, mime } = getSaveBlobAndName(format);
            
            try {
                if (window.showSaveFilePicker) {
                    let ext = '.' + format;
                    const handle = await window.showSaveFilePicker({ 
                        suggestedName: suggestedName, 
                        types: [{ description: format.toUpperCase() + ' File', accept: { [mime]: [ext] } }] 
                    });
                    const writable = await handle.createWritable(); 
                    await writable.write(blob); 
                    await writable.close(); 
                    showToast('성공적으로 저장되었습니다.');
                } else {
                    const url = URL.createObjectURL(blob); 
                    const a = document.createElement('a'); a.href = url; a.download = suggestedName; a.click();
                    showToast('저장되었습니다.');
                }
            } catch(e) { if (e.name !== 'AbortError') customAlert("저장 중 오류가 발생했습니다."); }
        }

        document.getElementById('btn_action_save').addEventListener('click', (e) => {
            if (e.target.closest('.dropdown-menu')) return;
            const format = document.getElementById('setting_save_format').value || 'png';
            performSave(format);
        });

        document.querySelectorAll('#dropdown_save button').forEach(btn => {
            btn.addEventListener('click', () => {
                const fmt = btn.getAttribute('data-format');
                performSave(fmt);
            });
        });

        
        document.getElementById('btn_add_text_to_shape').addEventListener('click', () => {
            const obj = canvas.getActiveObject();
            if (!obj || !['rect', 'ellipse', 'polygon'].includes(obj.type) || obj.linkedText) return;
            
            const txtColor = window.textColor || '#000000';
            const txtBgColor = typeof getTextBgOpacity === 'function' ? getTextBgOpacity() : '';
            const txtSize = parseInt(document.getElementById('text_size_input') ? document.getElementById('text_size_input').value : 50) || 50;
            const isBold = (document.getElementById('btn_txt_b') || {classList:{contains:()=>false}}).classList.contains('active');
            const isItalic = (document.getElementById('btn_txt_i') || {classList:{contains:()=>false}}).classList.contains('active');
            const isUnderline = (document.getElementById('btn_txt_u') || {classList:{contains:()=>false}}).classList.contains('active');
            
            const alignActive = document.querySelector('.btn-group .btn-align.active');
            const textAlign = alignActive ? alignActive.getAttribute('data-align') : 'center';

            const center = obj.getCenterPoint();
            
            let padW = 20;
            let startW = obj.width * obj.scaleX;
            if (obj.type === 'ellipse') {
                startW = startW * Math.cos(Math.PI / 4);
            } else if (obj.type === 'polygon' && obj.points && obj.points.length === 4) {
                startW = startW * 0.5;
            }
            startW = Math.max(50, startW - padW);

            const textObj = new fabric.Textbox('내용 입력', {
                left: center.x,
                top: center.y,
                originX: 'center',
                originY: 'center',
                width: startW,
                fontSize: txtSize,
                fill: txtColor,
                backgroundColor: txtBgColor === 'transparent' ? '' : txtBgColor,
                fontWeight: isBold ? 'bold' : 'normal',
                fontStyle: isItalic ? 'italic' : 'normal',
                underline: isUnderline,
                textAlign: textAlign,
                fontFamily: 'Pretendard',
                editable: true,
                hasControls: false,
                hasBorders: false,
                selectable: true,
                evented: true,     // 클릭 이벤트는 받아야 함
                splitByGrapheme: true,
                isWidthFixed: true,
                hoverCursor: 'move'
            });
            
            obj.linkedText = textObj;
            textObj.linkedShape = obj;
            
            textObj.on('editing:entered', function() {
                this.set('hoverCursor', 'text');
            });
            textObj.on('editing:exited', function() {
                this.set('hoverCursor', 'move');
            });
            
            canvas.add(textObj);
            
            obj.originalScaleX = obj.scaleX;
            obj.originalScaleY = obj.scaleY;
            obj.originalWidth = obj.width;
            obj.originalHeight = obj.height;
            obj._initHeight = obj.height * obj.scaleY; // Store initial visual height for shrink-back

            textObj.on('changed', function() {
                const shape = this.linkedShape;
                if (!shape) return;
                
                const padding = 20;
                // Calculate text area width from current shape dimensions
                let shapeVisualW = shape.width * shape.scaleX;
                let textAreaFactor = 1;
                if (shape.type === 'ellipse') textAreaFactor = Math.cos(Math.PI / 4);
                else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) textAreaFactor = 0.5;
                
                this.set({ width: Math.max(50, shapeVisualW * textAreaFactor - padding) });
                
                // Calculate required shape height for the text content
                let reqTextH = this.calcTextHeight() + padding;
                let heightFactor = 1;
                if (shape.type === 'ellipse') heightFactor = Math.cos(Math.PI / 4);
                else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) heightFactor = 0.5;
                let reqShapeH = reqTextH / heightFactor;
                
                // Minimum height is the initial creation height
                let minH = shape._initHeight || (shape.originalHeight * (shape.originalScaleY || 1));
                let currentH = shape.height * shape.scaleY;
                let targetH = Math.max(minH, reqShapeH);
                
                if (Math.abs(currentH - targetH) > 1) {
                    shape.scaleY = targetH / shape.height;
                }
                
                const center = shape.getCenterPoint();
                this.set({ left: center.x, top: center.y });
                this.setCoords();
                shape.setCoords();
                if (shape.canvas) {
                    shape.canvas.requestRenderAll();
                }
            });

            obj.setControlVisible('addText', false);
            
            canvas.setActiveObject(textObj);
            
            document.getElementById('sub_toolbar').style.display = 'block';
            document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
            document.getElementById('panel_text').classList.add('active');

            textObj.enterEditing();
            textObj.selectAll();
            canvas.requestRenderAll();
            saveHistory();
        });

        document.getElementById('btn_action_copy').addEventListener('click', async () => {
            if(!hasActiveCanvas) return;
            canvas.discardActiveObject(); 
            let oldClip = canvas.clipPath; canvas.clipPath = null; canvas.renderAll();
            const dataUrl = canvas.toDataURL({ format: 'png', quality: 1, multiplier: 1, left: 0, top: 0, width: canvas.width, height: canvas.height });
            canvas.clipPath = oldClip; canvas.renderAll();
            
            if (pyBackend) {
                pyBackend.copy_to_clipboard(dataUrl);
                showToast('클립보드에 복사되었습니다.');
            } else {
                try {
                    const res = await fetch(dataUrl); const blob = await res.blob();
                    await navigator.clipboard.write([new ClipboardItem({[blob.type]: blob})]);
                    showToast('클립보드에 복사되었습니다.');
                } catch(e) { showToast('복사 실패'); }
            }
        });

        // 완벽한 백그라운드 & 캔버스 인쇄 기능 (여백 완전 제거)
        document.getElementById('btn_action_print').addEventListener('click', () => { 
            if(!hasActiveCanvas) return;
            canvas.discardActiveObject();
            
            const prevZoom = canvas.getZoom();
            canvas.setZoom(1);
            const dataUrl = canvas.toDataURL({ format: 'png', quality: 1.0, left: 0, top: 0, width: canvas.width, height: canvas.height });
            canvas.setZoom(prevZoom);

            if (pyBackend) {
                pyBackend.print_image(dataUrl);
            } else {
                const printWindow = window.open('', '_blank');
                printWindow.document.write(`
                    <html><head><title>Capcraft 인쇄</title>
                    <style>
                        @page { size: ${canvas.width}px ${canvas.height}px; margin: 0; }
                        body { margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; background: white; min-height: 100vh; }
                        img { width: 100%; height: 100%; display: block; object-fit: contain; }
                    
        </style>
                    </head><body><img src="${dataUrl}" onload="setTimeout(() => { window.print(); window.close(); }, 250);"></body></html>
                `);
                printWindow.document.close();
            }
        });

        document.getElementById('btn_action_close').addEventListener('click', () => { window.close(); });

        // ==========================================
        // 6. 버튼 활성/비활성 제어 및 도구 로직
        // ==========================================
        const panels = { 'shape': 'panel_shape', 'pen': 'panel_pen', 'text': 'panel_text', 'eraser': 'panel_eraser', 'emoji': 'panel_emoji', 'image': 'panel_image', 'mosaic': 'panel_mosaic', 'crop': 'panel_crop' };

        function updatePenBrush() {
            if (activeTool !== 'pen') {
                canvas.isDrawingMode = false;
                return;
            }
            const mode = document.querySelector('input[name="pen_mode"]:checked').value;
            if (mode === 'normal') {
                canvas.isDrawingMode = true;
                if(!canvas.freeDrawingBrush || canvas.freeDrawingBrush.type !== 'pencil') {
                    canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
                }
                canvas.freeDrawingBrush.color = penCurrentColor;
                canvas.freeDrawingBrush.width = parseInt(document.getElementById('pen_weight').value) || 5;
                if (document.getElementById('pen_dashed').checked) {
                    canvas.freeDrawingBrush.strokeDashArray = [canvas.freeDrawingBrush.width * 3, canvas.freeDrawingBrush.width * 3];
                } else {
                    canvas.freeDrawingBrush.strokeDashArray = null;
                }
            } else {
                canvas.isDrawingMode = false;
            }
        }

        document.getElementById('pen_type').addEventListener('change', (e) => {
            const val = e.target.value;
            if (val === 'ballpoint') {
                document.getElementById('pen_weight').value = sysPenBallpointWeight;
                document.getElementById('btn_pen_color').style.backgroundColor = sysPenBallpointColor;
                penCurrentColor = sysPenBallpointColor;
            } else {
                document.getElementById('pen_weight').value = sysPenHighlighterWeight;
                document.getElementById('btn_pen_color').style.backgroundColor = sysPenHighlighterColor;
                penCurrentColor = sysPenHighlighterColor;
            }
            updatePenBrush();
        });

        document.getElementById('pen_weight').addEventListener('input', (e) => {
            const val = parseInt(e.target.value) || 1;
            if (document.getElementById('pen_type').value === 'ballpoint') {
                sysPenBallpointWeight = val;
                document.getElementById('set_pen_ballpoint_weight').value = val;
            } else {
                sysPenHighlighterWeight = val;
                document.getElementById('set_pen_highlighter_weight').value = val;
            }
            updatePenBrush();
        });

        document.getElementById('pen_dashed').addEventListener('change', updatePenBrush);
        document.querySelectorAll('input[name="pen_mode"]').forEach(r => r.addEventListener('change', updatePenBrush));

        document.querySelectorAll('.btn-tool.group-edit').forEach(btn => {
            btn.addEventListener('click', () => {
                if(!hasActiveCanvas) return;
                if(multiClickDrawing) finalizeMultiClickDrawing(); 
                
                if (btn.classList.contains('active')) {
                    btn.classList.remove('active'); activeTool = null;
                    document.getElementById('sub_toolbar').style.display = 'none'; document.getElementById('emoji_popup').style.display = 'none';
                    canvas.isDrawingMode = false;
                    document.getElementById('capture_overlay').style.display = 'none';
                    hideCropOverlay();
                    updateGlobalCursor();
                    return; 
                }
                
                document.querySelectorAll('.btn-tool.group-edit').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const toolName = btn.innerText;
                activeTool = null; document.getElementById('sub_toolbar').style.display = 'block';
                Object.values(panels).forEach(id => document.getElementById(id).classList.remove('active'));
                document.getElementById('emoji_popup').style.display = 'none'; 
                document.getElementById('capture_overlay').style.display = 'none';
                
                canvas.isDrawingMode = false;
                updateSubToolbarPosition(btn);

                if (toolName.includes('도형')) { activeTool = 'shape'; document.getElementById('panel_shape').classList.add('active'); }
                else if (toolName.includes('펜')) { activeTool = 'pen'; document.getElementById('panel_pen').classList.add('active'); updatePenBrush(); }
                else if (toolName.includes('텍스트')) { activeTool = 'text'; document.getElementById('panel_text').classList.add('active'); }
                else if (toolName.includes('이모티콘')) { 
                    activeTool = 'emoji'; 
                    document.getElementById('panel_emoji').classList.add('active'); 
                    document.getElementById('emoji_popup').style.display = 'block'; 
                    const toast = document.getElementById('toast_emoji_notice');
                    if (toast) {
                        toast.style.display = 'block';
                        setTimeout(() => toast.style.opacity = '1', 10);
                        setTimeout(() => {
                            toast.style.opacity = '0';
                            setTimeout(() => toast.style.display = 'none', 300);
                        }, 2000);
                    }
                }
                else if (toolName.includes('이미지')) { activeTool = 'image'; document.getElementById('panel_image').classList.add('active'); }
                else if (toolName.includes('지우개')) { activeTool = 'eraser'; document.getElementById('panel_eraser').classList.add('active'); }
                else if (toolName.includes('모자이크')) { activeTool = 'mosaic'; document.getElementById('panel_mosaic').classList.add('active'); }
                else if (toolName.includes('자르기')) { 
                    activeTool = 'crop'; document.getElementById('panel_crop').classList.add('active');
                    initCropOverlay();
                }
                updateShapeOptions(); 
                updateGlobalCursor();
            });
        });

        // ==========================================
        // 7. 새 배경 이미지 (색상농도 믹스 로직)
        // ==========================================
        window.createNewBackground = function() {
            const sizeArr = document.getElementById('new_bg_size').value.split('x'); 
            const intensity = parseInt(document.getElementById('new_bg_intensity').value) / 100;
            const rawColor = document.getElementById('new_bg_color').style.backgroundColor;
            
            const fColor = new fabric.Color(rawColor).getSource();
            const r = Math.round(255 - (255 - fColor[0]) * intensity);
            const g = Math.round(255 - (255 - fColor[1]) * intensity);
            const b = Math.round(255 - (255 - fColor[2]) * intensity);
            const bgColor = `rgb(${r}, ${g}, ${b})`;

            if (hasActiveCanvas) pushCurrentToRecent();
            activeRecentIdx = -1;
            stateHistory = []; historyIndex = -1;
            isHistoryAction = true; canvas.clear(); 
            commitLoadToCanvas(null, parseInt(sizeArr[0]), parseInt(sizeArr[1]), bgColor);
            closeModals(); 
        };

        document.getElementById('btn_open_new_bg').addEventListener('click', () => openModal('modal_new_bg'));

        // 비율 잠금 로직
        document.getElementById('edit_shape_w').addEventListener('input', e => { if(document.getElementById('edit_shape_lock_ratio').checked) document.getElementById('edit_shape_h').value = Math.round(e.target.value / origShapeRatio); });
        document.getElementById('edit_shape_h').addEventListener('input', e => { if(document.getElementById('edit_shape_lock_ratio').checked) document.getElementById('edit_shape_w').value = Math.round(e.target.value * origShapeRatio); });
        document.getElementById('edit_image_w').addEventListener('input', e => { if(document.getElementById('edit_image_lock_ratio').checked) document.getElementById('edit_image_h').value = Math.round(e.target.value / origImageRatio); });
        document.getElementById('edit_image_h').addEventListener('input', e => { if(document.getElementById('edit_image_lock_ratio').checked) document.getElementById('edit_image_w').value = Math.round(e.target.value * origImageRatio); });
        document.getElementById('edit_line_w').addEventListener('input', e => { if(document.getElementById('edit_line_lock_ratio').checked) document.getElementById('edit_line_h').value = Math.round(e.target.value / origLineRatio); });
        document.getElementById('edit_line_h').addEventListener('input', e => { if(document.getElementById('edit_line_lock_ratio').checked) document.getElementById('edit_line_w').value = Math.round(e.target.value * origLineRatio); });

        // 개체 더블클릭 속성 수정창 (JSON 로드 개체 대응 완벽 동기화)
        canvas.on('mouse:dblclick', function(o) {
            if(multiClickDrawing) { finalizeMultiClickDrawing(); return; } 
            if(activeTool) return; 
            
            let targetObj = o.target || canvas.findTarget(o.e, false);
            if (!targetObj) return;
            editingObject = targetObj; 
            
            const isText = (editingObject.type === 'i-text' || editingObject.type === 'text');
            const isEmoji = editingObject.isEmoji || (isText && !editingObject.text.match(/[a-zA-Z가-힣0-9]/)); 
            const isImage = (editingObject.type === 'image' && !editingObject.isMosaic) || editingObject.isMediaImage;
            const isArrow = (editingObject.type === 'group'); 
            const isLinePath = (editingObject.type === 'line' || editingObject.type === 'path' || editingObject.type === 'polyline' || isArrow);
            const isRectEllipse = (editingObject.type === 'rect' || editingObject.type === 'ellipse' || editingObject.type === 'polygon' || editingObject.type === 'circle');

            document.getElementById('form_edit_text').style.display = 'none';
            document.getElementById('form_edit_shape').style.display = 'none';
            document.getElementById('form_edit_line').style.display = 'none';
            document.getElementById('form_edit_emoji').style.display = 'none';
            document.getElementById('form_edit_image').style.display = 'none';

            if (isEmoji) {
                document.getElementById('form_edit_emoji').style.display = 'block';
                const currentSize = editingObject.baseFontSize ? Math.round(editingObject.baseFontSize * editingObject.scaleX) : (editingObject.fontSize || 36);
                document.getElementById('edit_emoji_size').value = currentSize;
            } 
            else if (isImage) {
                document.getElementById('form_edit_image').style.display = 'block';
                let imgW, imgH;
                if (editingObject.type === 'group') {
                    imgW = editingObject.getObjects()[0].width;
                    imgH = editingObject.getObjects()[0].height;
                } else {
                    imgW = editingObject.width;
                    imgH = editingObject.height;
                }
                document.getElementById('edit_image_w').value = Math.round(imgW * editingObject.scaleX);
                document.getElementById('edit_image_h').value = Math.round(imgH * editingObject.scaleY);
                origImageRatio = (imgW * editingObject.scaleX) / (imgH * editingObject.scaleY);
            } 
            else if (isText && !isEmoji) {
                document.getElementById('form_edit_text').style.display = 'block';
                document.getElementById('edit_text_size').value = editingObject.fontSize;
                document.getElementById('edit_text_content').value = editingObject.text;
                document.getElementById('edit_btn_b').classList.toggle('active', editingObject.fontWeight === 'bold');
                document.getElementById('edit_btn_i').classList.toggle('active', editingObject.fontStyle === 'italic');
                document.getElementById('edit_btn_u').classList.toggle('active', editingObject.underline);
                
                document.querySelectorAll('#edit_text_align_group .btn-align').forEach(btn => {
                    btn.classList.toggle('active', btn.getAttribute('data-align') === (editingObject.textAlign || 'left'));
                });
                document.getElementById('edit_text_align').value = editingObject.textAlign || 'center';
                
                document.getElementById('edit_text_color').style.backgroundColor = editingObject.fill || '#000';
                let bCol = editingObject.backgroundColor;
                document.getElementById('edit_text_bg').style.backgroundColor = (bCol && bCol !== 'rgba(0,0,0,0)') ? bCol : 'transparent';
                document.getElementById('edit_text_bg').style.backgroundImage = (bCol && bCol !== 'rgba(0,0,0,0)') ? 'none' : 'linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc)';
            } 
            else if (isRectEllipse) {
                document.getElementById('form_edit_shape').style.display = 'block';
                
                let ew = 0, eh = 0;
                if(editingObject.type === 'rect') {
                    ew = Math.round(editingObject.width * editingObject.scaleX);
                    eh = Math.round(editingObject.height * editingObject.scaleY);
                } else if(editingObject.type === 'ellipse') {
                    ew = Math.round(editingObject.rx * 2 * editingObject.scaleX);
                    eh = Math.round(editingObject.ry * 2 * editingObject.scaleY);
                } else if(editingObject.type === 'circle') {
                    ew = Math.round(editingObject.radius * 2 * editingObject.scaleX);
                    eh = Math.round(editingObject.radius * 2 * editingObject.scaleY);
                } else if(editingObject.type === 'polygon') {
                    ew = Math.round(editingObject.width * editingObject.scaleX);
                    eh = Math.round(editingObject.height * editingObject.scaleY);
                }
                document.getElementById('edit_shape_w').value = ew;
                document.getElementById('edit_shape_h').value = eh;
                origShapeRatio = ew / eh;
                
                document.getElementById('edit_shape_weight').value = editingObject.strokeWidth || 0; 
                document.getElementById('edit_shape_stroke').style.backgroundColor = editingObject.stroke || '#000'; 
                document.getElementById('edit_shape_dashed').checked = !!(editingObject.strokeDashArray && editingObject.strokeDashArray.length > 0);

                let fCol = editingObject.fill;
                if(fCol && fCol.indexOf('rgba') > -1) { fCol = fCol.replace(/rgba?\((\d+),\s*(\d+),\s*(\d+).*/, 'rgb($1,$2,$3)'); }
                document.getElementById('edit_shape_fill').style.backgroundColor = fCol || 'transparent';
                document.getElementById('edit_shape_fill').style.backgroundImage = (!fCol || fCol === 'transparent') ? 'linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc)' : 'none';
            } 
            else if (isLinePath) {
                document.getElementById('form_edit_line').style.display = 'block';
                
                let sCol = editingObject.stroke;
                let sWeight = editingObject.strokeWidth;
                let fCol = editingObject.fill;
                let isDashed = !!(editingObject.strokeDashArray && editingObject.strokeDashArray.length > 0);
                let scale = editingObject.scaleX;

                let ew = 0, eh = 0;
                if (isArrow && editingObject.getObjects) {
                    let objs = editingObject.getObjects();
                    ew = Math.round(editingObject.width * editingObject.scaleX);
                    eh = Math.round(editingObject.height * editingObject.scaleY);
                    let lineObj = objs.find(o => o.isArrowBody || (o.strokeWidth && o.strokeWidth > 0 && o.stroke !== 'transparent'));
                    if (lineObj) {
                        sCol = lineObj.stroke || lineObj.fill;
                        sWeight = lineObj.strokeWidth;
                        fCol = lineObj.fill;
                        isDashed = !!(lineObj.strokeDashArray && lineObj.strokeDashArray.length > 0);
                    }
                } else if (editingObject.type === 'path' || editingObject.type === 'line') {
                    sCol = editingObject.stroke;
                    ew = Math.round(editingObject.width * editingObject.scaleX);
                    eh = Math.round(editingObject.height * editingObject.scaleY);
                }
                
                document.getElementById('edit_line_w').value = ew;
                document.getElementById('edit_line_h').value = eh;
                origLineRatio = (eh === 0) ? 1 : ew / eh;

                document.getElementById('edit_line_weight').value = sWeight || 0;
                document.getElementById('edit_line_stroke').style.backgroundColor = sCol || '#000';
                document.getElementById('edit_line_dashed').checked = isDashed;

                if(fCol && fCol.indexOf('rgba') > -1) { fCol = fCol.replace(/rgba?\((\d+),\s*(\d+),\s*(\d+).*/, 'rgb($1,$2,$3)'); }
                document.getElementById('edit_line_fill').style.backgroundColor = fCol || 'transparent';
                document.getElementById('edit_line_fill').style.backgroundImage = (!fCol || fCol === 'transparent') ? 'linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc)' : 'none';
            }

            openModal('modal_edit');
        });

        window.applyObjectEdit = function() {
            if (!editingObject) return;
            const isText = (editingObject.type === 'i-text' || editingObject.type === 'text');
            const isEmoji = editingObject.isEmoji || (isText && !editingObject.text.match(/[a-zA-Z가-힣0-9]/));
            const isImage = (editingObject.type === 'image' && !editingObject.isMosaic) || editingObject.isMediaImage;
            const isArrow = (editingObject.type === 'group'); 
            const isRectEllipse = (editingObject.type === 'rect' || editingObject.type === 'ellipse' || editingObject.type === 'polygon' || editingObject.type === 'circle');
            const isLinePath = (editingObject.type === 'line' || editingObject.type === 'path' || editingObject.type === 'polyline' || isArrow);

            if (isEmoji) {
                const size = parseInt(document.getElementById('edit_emoji_size').value);
                if (editingObject.baseFontSize) { // Image로 변환된 새 이모티콘
                    const scale = size / editingObject.baseFontSize;
                    editingObject.set({ scaleX: scale, scaleY: scale });
                } else { // 예전 버전 호환성 (fabric.Text로 저장된 경우)
                    editingObject.set({ fontSize: size });
                }
                editingObject.setCoords();
            } else if (isImage) {
                const newW = parseInt(document.getElementById('edit_image_w').value);
                const newH = parseInt(document.getElementById('edit_image_h').value);
                let baseW = editingObject.type === 'group' ? editingObject.getObjects()[0].width : editingObject.width;
                let baseH = editingObject.type === 'group' ? editingObject.getObjects()[0].height : editingObject.height;
                editingObject.set({ scaleX: newW / baseW, scaleY: newH / baseH });
                editingObject.setCoords();
            } else if (isText && !isEmoji) {
                const size = parseInt(document.getElementById('edit_text_size').value);
                const tColor = document.getElementById('edit_text_color').style.backgroundColor;
                let bColor = document.getElementById('edit_text_bg').style.backgroundColor;
                if(bColor === 'rgba(0, 0, 0, 0)') bColor = 'transparent';

                editingObject.set({ 
                    text: document.getElementById('edit_text_content').value,
                    fontSize: size, fill: tColor, backgroundColor: bColor === 'transparent' ? '' : bColor,
                    fontWeight: document.getElementById('edit_btn_b').classList.contains('active') ? 'bold' : 'normal',
                    fontStyle: document.getElementById('edit_btn_i').classList.contains('active') ? 'italic' : 'normal',
                    underline: document.getElementById('edit_btn_u').classList.contains('active'),
                    textAlign: document.getElementById('edit_text_align').value
                });
                editingObject.setCoords();
            } else if (isRectEllipse) {
                const newW = parseInt(document.getElementById('edit_shape_w').value);
                const newH = parseInt(document.getElementById('edit_shape_h').value);
                const size = parseInt(document.getElementById('edit_shape_weight').value);
                const sColor = document.getElementById('edit_shape_stroke').style.backgroundColor;
                const isDashed = document.getElementById('edit_shape_dashed').checked;
                const dashArr = isDashed ? [size * 3, size * 3] : null;

                let rawFColor = document.getElementById('edit_shape_fill').style.backgroundColor;
                let finalFill = 'transparent';
                if(rawFColor !== 'rgba(0, 0, 0, 0)' && rawFColor !== 'transparent' && rawFColor !== '') {
                    finalFill = new fabric.Color(rawFColor).setAlpha(sysShapeOpacity).toRgba();
                }

                if (editingObject.type === 'rect') {
                    editingObject.set({ width: newW, height: newH, scaleX: 1, scaleY: 1, strokeWidth: size, strokeDashArray: dashArr, stroke: sColor, fill: finalFill }); 
                } else if (editingObject.type === 'ellipse') {
                    editingObject.set({ rx: newW/2, ry: newH/2, scaleX: 1, scaleY: 1, strokeWidth: size, strokeDashArray: dashArr, stroke: sColor, fill: finalFill }); 
                } else if (editingObject.type === 'circle') {
                    editingObject.set({ radius: newW/2, scaleX: 1, scaleY: 1, strokeWidth: size, strokeDashArray: dashArr, stroke: sColor, fill: finalFill }); 
                } else if (editingObject.type === 'polygon') {
                    // Polygon scaling
                    const scaleX = (editingObject.width > 0) ? newW / editingObject.width : 1;
                    const scaleY = (editingObject.height > 0) ? newH / editingObject.height : 1;
                    let m = editingObject.calcTransformMatrix();
                    let minX = Math.min(...editingObject.points.map(p=>p.x)), minY = Math.min(...editingObject.points.map(p=>p.y));
                    let newPts = editingObject.points.map(pt => {
                        return { x: minX + (pt.x - minX) * scaleX, y: minY + (pt.y - minY) * scaleY };
                    });
                    editingObject.set({ points: newPts, scaleX: 1, scaleY: 1, width: newW, height: newH, strokeWidth: size, strokeDashArray: dashArr, stroke: sColor, fill: finalFill });
                }
                editingObject.setCoords();
            } else if (isLinePath) {
                const size = parseInt(document.getElementById('edit_line_weight').value);
                const sColor = document.getElementById('edit_line_stroke').style.backgroundColor;
                const isDashed = document.getElementById('edit_line_dashed').checked;
                const dashArr = isDashed ? [size * 3, size * 3] : null;

                let rawLineFColor = document.getElementById('edit_line_fill').style.backgroundColor;
                let finalLineFill = 'transparent';
                if(rawLineFColor !== 'rgba(0, 0, 0, 0)' && rawLineFColor !== 'transparent' && rawLineFColor !== '') {
                    finalLineFill = new fabric.Color(rawLineFColor).setAlpha(sysShapeOpacity).toRgba();
                }
                
                const newW = parseInt(document.getElementById('edit_line_w').value);
                const newH = parseInt(document.getElementById('edit_line_h').value);
                const scaleX = (editingObject.width  > 0) ? newW / editingObject.width  : 1;
                const scaleY = (editingObject.height > 0) ? newH / editingObject.height : 1;
                
                if (isArrow || editingObject.type === 'path') {
                    let oldBody = isArrow ? editingObject.getObjects().find(o => o.isArrowBody) : editingObject;
                    let m = oldBody.calcTransformMatrix();
                    let po = oldBody.pathOffset || { x: 0, y: 0 };
                    
                    let absPoints = [];
                    oldBody.path.forEach(cmd => {
                        if(cmd[0] === 'M' || cmd[0] === 'L') absPoints.push(fabric.util.transformPoint({x: cmd[1] - po.x, y: cmd[2] - po.y}, m));
                        else if(cmd[0] === 'C') absPoints.push(fabric.util.transformPoint({x: cmd[5] - po.x, y: cmd[6] - po.y}, m));
                        else if(cmd[0] === 'Q') absPoints.push(fabric.util.transformPoint({x: cmd[3] - po.x, y: cmd[4] - po.y}, m));
                    });
                    
                    let minX = Math.min(...absPoints.map(p=>p.x)), minY = Math.min(...absPoints.map(p=>p.y));
                    
                    let newPathStr = "";
                    let finalP = null, prevP = null;
                    oldBody.path.forEach(cmd => {
                        if(cmd[0] === 'M' || cmd[0] === 'L') {
                            let p = fabric.util.transformPoint({x: cmd[1] - po.x, y: cmd[2] - po.y}, m);
                            let sx = minX + (p.x - minX) * scaleX; let sy = minY + (p.y - minY) * scaleY;
                            newPathStr += `${cmd[0]} ${sx} ${sy} `;
                            prevP = finalP; finalP = {x: sx, y: sy};
                        } else if(cmd[0] === 'C') {
                            let cp1 = fabric.util.transformPoint({x: cmd[1] - po.x, y: cmd[2] - po.y}, m);
                            let cp2 = fabric.util.transformPoint({x: cmd[3] - po.x, y: cmd[4] - po.y}, m);
                            let p = fabric.util.transformPoint({x: cmd[5] - po.x, y: cmd[6] - po.y}, m);
                            let sx1 = minX + (cp1.x - minX) * scaleX; let sy1 = minY + (cp1.y - minY) * scaleY;
                            let sx2 = minX + (cp2.x - minX) * scaleX; let sy2 = minY + (cp2.y - minY) * scaleY;
                            let sx = minX + (p.x - minX) * scaleX; let sy = minY + (p.y - minY) * scaleY;
                            newPathStr += `${cmd[0]} ${sx1} ${sy1}, ${sx2} ${sy2}, ${sx} ${sy} `;
                            prevP = finalP; finalP = {x: sx, y: sy};
                        } else if(cmd[0] === 'Q') {
                            let cp1 = fabric.util.transformPoint({x: cmd[1] - po.x, y: cmd[2] - po.y}, m);
                            let p = fabric.util.transformPoint({x: cmd[3] - po.x, y: cmd[4] - po.y}, m);
                            let sx1 = minX + (cp1.x - minX) * scaleX; let sy1 = minY + (cp1.y - minY) * scaleY;
                            let sx = minX + (p.x - minX) * scaleX; let sy = minY + (p.y - minY) * scaleY;
                            newPathStr += `${cmd[0]} ${sx1} ${sy1}, ${sx} ${sy} `;
                            prevP = finalP; finalP = {x: sx, y: sy};
                        }
                    });
                    
                    let newObj;
                    if (isArrow && finalP && prevP) {
                        let arrowType = oldBody.arrowType || editingObject.arrowType || sysArrowType;
                        let arrowSize = oldBody.arrowSize || editingObject.arrowSize || sysArrowSize;
                        let angle = Math.atan2(finalP.y - prevP.y, finalP.x - prevP.x);
                        let sizeMult = arrowSize === 'xs' ? 1.5 : arrowSize === 's' ? 2 : arrowSize === 'l' ? 4 : 3;
                        let w = size * sizeMult + 8;
                        let pullBack = (arrowType === 'stealth') ? w * 0.6 : (arrowType === 'open') ? 0 : w;
                        let adjFinalX = finalP.x - Math.cos(angle) * pullBack;
                        let adjFinalY = finalP.y - Math.sin(angle) * pullBack;
                        let parts = newPathStr.trim().split(' ');
                        parts[parts.length-2] = adjFinalX;
                        parts[parts.length-1] = adjFinalY;
                        newPathStr = parts.join(' ');
                        let newBody = new fabric.Path(newPathStr, { fill: 'transparent', stroke: sColor, strokeWidth: size, strokeDashArray: dashArr, strokeLineCap: 'round', strokeLineJoin: 'round', isArrowBody: true, objectCaching: false, arrowType: arrowType, arrowSize: arrowSize });
                        let newHead = createArrowHead(finalP.x, finalP.y, angle, arrowType, arrowSize, sColor, size);
                        newObj = new fabric.Group([newBody, newHead], { selectable: true, evented: true, arrowType: arrowType, arrowSize: arrowSize });
                    } else {
                        newObj = new fabric.Path(newPathStr, { fill: finalLineFill, stroke: sColor, strokeWidth: size, strokeDashArray: dashArr, strokeLineCap: 'round', strokeLineJoin: 'round', selectable: true, evented: true, objectCaching: true });
                    }
                    
                    canvas.remove(editingObject);
                    canvas.add(newObj);
                    canvas.setActiveObject(newObj);
                    editingObject = newObj;
                    editingObject.setCoords();
                } else {
                    editingObject.set({ strokeWidth: size, stroke: sColor, strokeDashArray: dashArr, fill: finalLineFill });
                    editingObject.setCoords();
                }
            }
            canvas.requestRenderAll();
            saveHistory();
            closeModals();
        };

        function updateActiveText(propName = null, propValue = null, skipSelection = false) {
            if (propName && typeof propName === 'object') { propName = null; propValue = null; }
            const obj = canvas.getActiveObject();
            if (!obj) return;
            const targetText = obj.linkedText || (['i-text', 'textbox', 'text'].includes(obj.type) && !obj.isEmoji ? obj : null);
            if (targetText) {
                const hasSelection = targetText.isEditing && targetText.selectionStart !== targetText.selectionEnd;

                if (propName) {
                    if (!skipSelection && hasSelection && propName !== 'textAlign' && propName !== 'backgroundColor') {
                        const styleObj = {}; styleObj[propName] = propValue;
                        targetText.setSelectionStyles(styleObj);
                    } else {
                        targetText.set(propName, propValue);
                    }
                } else {
                    const isB = document.getElementById('btn_txt_b') && document.getElementById('btn_txt_b').classList.contains('active');
                    const isI = document.getElementById('btn_txt_i') && document.getElementById('btn_txt_i').classList.contains('active');
                    const isU = document.getElementById('btn_txt_u') && document.getElementById('btn_txt_u').classList.contains('active');
                    const fw = isB ? 'bold' : 'normal';
                    const fst = isI ? 'italic' : 'normal';
                    const und = !!isU;
                    const fs = parseInt(document.getElementById('text_size_input').value) || 50;
                    let alignVal = 'center';
                    if (document.getElementById('text_align')) alignVal = document.getElementById('text_align').value;
                    if (document.getElementById('edit_text_align')) alignVal = document.getElementById('edit_text_align').value;

                    if (!skipSelection && hasSelection) {
                        targetText.setSelectionStyles({ fontWeight: fw, fontStyle: fst, underline: und, fontSize: fs, fill: textColor });
                    } else {
                        targetText.set({ fontWeight: fw, fontStyle: fst, underline: und, fontSize: fs, fill: textColor, backgroundColor: getTextBgOpacity(), textAlign: alignVal });
                    }
                }
                targetText.dirty = true;
                if (targetText.isEditing && targetText.initDimensions) {
                    targetText.initDimensions();
                }
                if (targetText.linkedShape) targetText.fire('changed');
                canvas.requestRenderAll();
            }
        }
        ['b','i','u'].forEach(type => { 
            const topBtn = document.getElementById('btn_txt_'+type);
            const editBtn = document.getElementById('edit_btn_'+type);
            function onClick() {
                this.classList.toggle('active'); 
                const isActive = this.classList.contains('active');
                if (editBtn && this === topBtn) editBtn.classList.toggle('active', isActive);
                if (topBtn && this === editBtn) topBtn.classList.toggle('active', isActive);
                
                let pName, pVal;
                if(type === 'b') { pName = 'fontWeight'; pVal = isActive ? 'bold' : 'normal'; }
                if(type === 'i') { pName = 'fontStyle'; pVal = isActive ? 'italic' : 'normal'; }
                if(type === 'u') { pName = 'underline'; pVal = isActive; }
                updateActiveText(pName, pVal);
            }
            if (topBtn) { topBtn.addEventListener('mousedown', e => e.preventDefault()); topBtn.addEventListener('click', onClick); }
            if (editBtn) { editBtn.addEventListener('mousedown', e => e.preventDefault()); editBtn.addEventListener('click', onClick); }
        });
        
        document.querySelectorAll('.btn-align').forEach(btn => {
            btn.addEventListener('mousedown', e => e.preventDefault());
            btn.addEventListener('click', function() {
                const group = this.closest('.btn-group');
                if (group) {
                    group.querySelectorAll('.btn-align').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    const val = this.getAttribute('data-align');
                    
                    if (group.id === 'edit_text_align_group') {
                        document.getElementById('edit_text_align').value = val;
                        if (document.getElementById('text_align')) document.getElementById('text_align').value = val;
                    } else {
                        // main toolbar align group
                        if (document.getElementById('text_align')) {
                            document.getElementById('text_align').value = val;
                            if (document.getElementById('edit_text_align')) document.getElementById('edit_text_align').value = val;
                        }
                    }
                    updateActiveText('textAlign', val);
                }
            });
        });

        
        const sizeInput = document.getElementById('text_size_input');
        if (sizeInput) {
            sizeInput.addEventListener('input', function() { updateActiveText('fontSize', parseInt(this.value) || 50); });
            sizeInput.addEventListener('change', function() { updateActiveText('fontSize', parseInt(this.value) || 50); });
        }
        const editSizeInput = document.getElementById('edit_text_size');
        if (editSizeInput) {
            editSizeInput.addEventListener('input', function() {
                const val = parseInt(this.value) || 50;
                if(document.getElementById('text_size_input')) {
                    document.getElementById('text_size_input').value = val;
                }
                updateActiveText('fontSize', val);
            });
        }

        document.querySelector('emoji-picker').addEventListener('emoji-click', event => { 
            const clickedUrl = event.detail.url || (event.detail.emoji && event.detail.emoji.url);
            if (clickedUrl) {
                selectedEmojiUrl = clickedUrl;
                selectedEmoji = null;
                document.getElementById('emoji_preview').innerHTML = `<img src="${clickedUrl}" style="width:24px; height:24px; object-fit:contain; vertical-align:middle;">`;
            } else {
                selectedEmoji = event.detail.unicode || (event.detail.emoji && event.detail.emoji.unicode); 
                selectedEmojiUrl = null;
                document.getElementById('emoji_preview').innerText = selectedEmoji || "😀";
            }
            document.getElementById('emoji_popup').style.display = 'none'; 
        });
        document.getElementById('emoji_preview').addEventListener('click', () => document.getElementById('emoji_popup').style.display = 'block');
        
        let imageInsertData = null; // { src, frame, sx, sy, sw, sh }
        let insertImgOrigW = 0, insertImgOrigH = 0, insertScale = 1;
        
        document.getElementById('image_upload').addEventListener('change', function(e) { 
            const file = e.target.files[0]; if (!file) return; 
            const reader = new FileReader(); 
            reader.onload = function(f) {
                uploadedImageSrc = f.target.result; // ★ 반드시 저장
                const img = new Image();
                img.onload = () => {
                    insertImgOrigW = img.width; insertImgOrigH = img.height;
                    const container = document.getElementById('image_insert_preview_container');
                    // 모달이 아직 닫혀있을 수 있으므로 먼저 열어야 clientWidth가 정확함
                    openModal('modal_image_insert');
                    
                    requestAnimationFrame(() => {
                        const cW = container.clientWidth || 460;
                        const cH = container.clientHeight || 350;
                        insertScale = Math.min(cW / img.width, cH / img.height);
                        if (insertScale > 1) insertScale = 1;
                        
                        const pImg = document.getElementById('image_insert_img');
                        pImg.src = f.target.result;
                        pImg.style.display = 'block'; // ★ 보이게 설정
                        pImg.style.width  = img.width  + 'px';
                        pImg.style.height = img.height + 'px';
                        pImg.style.transform = `scale(${insertScale})`;
                        pImg.style.left = (cW - img.width  * insertScale) / 2 + 'px';
                        pImg.style.top  = (cH - img.height * insertScale) / 2 + 'px';
                        
                        document.getElementById('image_insert_selection').style.display = 'none';
                        imageInsertData = { src: f.target.result, frame: document.getElementById('image_insert_frame').value || 'rect', sx: 0, sy: 0, sw: img.width, sh: img.height };
                    });
                };
                img.src = f.target.result;
            }; 
            reader.readAsDataURL(file); 
        });

        
        const insertContainer = document.getElementById('image_insert_preview_container');
        const insertSelection = document.getElementById('image_insert_selection');
        let insertIsDragging = false, insertStartX = 0, insertStartY = 0;
        
        insertContainer.addEventListener('mousedown', e => {
            insertIsDragging = true;
            const rect = insertContainer.getBoundingClientRect();
            insertStartX = e.clientX - rect.left;
            insertStartY = e.clientY - rect.top;
            insertSelection.style.display = 'block';
            insertSelection.style.left = insertStartX + 'px';
            insertSelection.style.top = insertStartY + 'px';
            insertSelection.style.width = '0px'; insertSelection.style.height = '0px';
        });
        
        insertContainer.addEventListener('mousemove', e => {
            if(!insertIsDragging) return;
            const rect = insertContainer.getBoundingClientRect();
            let curX = e.clientX - rect.left; let curY = e.clientY - rect.top;
            
            curX = Math.max(0, Math.min(rect.width, curX));
            curY = Math.max(0, Math.min(rect.height, curY));
            
            let frame = document.getElementById('image_insert_frame').value;
            let w = Math.abs(curX - insertStartX); let h = Math.abs(curY - insertStartY);
            let left = Math.min(insertStartX, curX); let top = Math.min(insertStartY, curY);
            
            if (frame === 'square' || frame === 'circle') {
                let size = Math.min(w, h); w = size; h = size;
                left = curX < insertStartX ? insertStartX - size : insertStartX;
                top = curY < insertStartY ? insertStartY - size : insertStartY;
            }
            
            insertSelection.style.left = left + 'px';
            insertSelection.style.top = top + 'px';
            insertSelection.style.width = w + 'px';
            insertSelection.style.height = h + 'px';
            
            if(frame === 'circle' || frame === 'ellipse') insertSelection.style.borderRadius = '50%';
            else insertSelection.style.borderRadius = '0';
        });
        
        window.addEventListener('mouseup', () => { 
            if(insertIsDragging) {
                insertIsDragging = false;
                const pImg = document.getElementById('image_insert_img');
                const sel = insertSelection;
                const frame = document.getElementById('image_insert_frame').value;
                
                let sLeft = parseFloat(sel.style.left); let sTop = parseFloat(sel.style.top);
                let sWidth = parseFloat(sel.style.width); let sHeight = parseFloat(sel.style.height);
                let iLeft = parseFloat(pImg.style.left); let iTop = parseFloat(pImg.style.top);
                
                let cropX = (sLeft - iLeft) / insertScale;
                let cropY = (sTop - iTop) / insertScale;
                let cropW = sWidth / insertScale;
                let cropH = sHeight / insertScale;
                
                if (cropW < 5 || cropH < 5) {
                    cropX = 0; cropY = 0; cropW = insertImgOrigW; cropH = insertImgOrigH;
                    sel.style.display = 'none';
                }
                
                if(cropX < 0) { cropW += cropX; cropX = 0; }
                if(cropY < 0) { cropH += cropY; cropY = 0; }
                if(cropX + cropW > insertImgOrigW) cropW = insertImgOrigW - cropX;
                if(cropY + cropH > insertImgOrigH) cropH = insertImgOrigH - cropY;
                
                imageInsertData = { src: pImg.src, frame: frame, sx: cropX, sy: cropY, sw: cropW, sh: cropH };
            }
        });
        
        // ★ 이미지 삽입 — 버튼 클릭 시 캔버스 중앙에 즉시 배치 (드래그 불필요)
        function placeImageOnCanvas(src, cropX, cropY, cropW, cropH, frame) {
            if (!src || !hasActiveCanvas) return;
            closeModals();
            fabric.Image.fromURL(src, (img) => {
                // crop 적용
                img.set({ cropX: cropX, cropY: cropY, width: cropW, height: cropH });

                // 클립 마스크 (원/타원)
                if (frame === 'circle' || frame === 'ellipse') {
                    img.set({ clipPath: new fabric.Ellipse({
                        originX: 'center', originY: 'center',
                        rx: cropW / 2, ry: cropH / 2
                    })});
                }

                // 캔버스 80% 안에 들어오도록 스케일 조정
                const maxScale = Math.min(
                    (canvas.width  * 0.8) / cropW,
                    (canvas.height * 0.8) / cropH,
                    1
                );
                img.set({
                    originX: 'center', originY: 'center',
                    left: canvas.width  / 2,
                    top:  canvas.height / 2,
                    scaleX: maxScale,
                    scaleY: maxScale,
                    selectable: true,
                    evented: true,
                    isMediaImage: true,
                    frameType: frame
                });

                canvas.add(img);
                canvas.setActiveObject(img);
                canvas.bringToFront(img);
                canvas.requestRenderAll();
                saveHistory();
                // 이미지 툴 비활성화 (선택 모드로 복귀)
                const imgBtn = document.getElementById('btn_tool_image');
                if (imgBtn && imgBtn.classList.contains('active')) imgBtn.click();
            });
        }

        document.getElementById('btn_insert_original').addEventListener('click', () => {
            if (!uploadedImageSrc) { customAlert('이미지를 먼저 선택하세요.'); return; }
            placeImageOnCanvas(uploadedImageSrc, 0, 0, insertImgOrigW, insertImgOrigH, 'rect');
        });

        document.getElementById('btn_confirm_image_insert').addEventListener('click', () => {
            if (!imageInsertData || !imageInsertData.src) {
                customAlert('이미지를 먼저 선택하고 영역을 지정하세요.');
                return;
            }
            placeImageOnCanvas(
                imageInsertData.src,
                imageInsertData.sx, imageInsertData.sy,
                imageInsertData.sw, imageInsertData.sh,
                imageInsertData.frame
            );
        });
        
        document.getElementById('btn_clear_all').addEventListener('click', async () => { 
            const confirm = await customConfirm("그린 개체를 모두 지우시겠습니까?\n(배경/캡처 이미지는 삭제되지 않습니다.)");
            if (confirm) {
                const objs = canvas.getObjects().slice(); 
                objs.forEach(obj => canvas.remove(obj));
                canvas.requestRenderAll();
                saveHistory(); 
            }
        });

        // ==========================================
        // 화살표/도형 생성 도우미 (오차 없는 절대 좌표 변환 알고리즘 적용)
        // ==========================================
        function createArrowHead(x2, y2, angle, type, size, color, weight) {
            const sizeMult = size === 'xs' ? 1.5 : size === 's' ? 2 : size === 'l' ? 4 : 3;
            const w = weight * sizeMult + 8; 
            const h = w / 2;

            // 좌표를 삼각함수로 사전 회전시켜 바운딩 박스 오차 원천 차단
            const rotatePoint = (px, py, ang) => {
                return {
                    x: x2 + px * Math.cos(ang) - py * Math.sin(ang),
                    y: y2 + px * Math.sin(ang) + py * Math.cos(ang)
                };
            };

            const pTip = rotatePoint(0, 0, angle);
            const pTop = rotatePoint(-w, -h, angle);
            const pBot = rotatePoint(-w, h, angle);
            const pInner = rotatePoint(-w * 0.6, 0, angle);

            let pathStr = '';
            if (type === 'stealth') {
                pathStr = `M ${pTip.x} ${pTip.y} L ${pTop.x} ${pTop.y} L ${pInner.x} ${pInner.y} L ${pBot.x} ${pBot.y} Z`;
            } else if (type === 'open') {
                pathStr = `M ${pTop.x} ${pTop.y} L ${pTip.x} ${pTip.y} L ${pBot.x} ${pBot.y}`;
                return new fabric.Path(pathStr, {
                    fill: 'transparent', stroke: color, strokeWidth: weight,
                    strokeLineCap: 'round', strokeLineJoin: 'round',
                    selectable: false, isTemp: true, objectCaching: false,
                    isArrowHead: true
                });
            } else { 
                pathStr = `M ${pTip.x} ${pTip.y} L ${pTop.x} ${pTop.y} L ${pBot.x} ${pBot.y} Z`;
            }

            return new fabric.Path(pathStr, {
                fill: color, stroke: 'transparent', strokeWidth: 0, 
                selectable: false, isTemp: true, objectCaching: false, strokeLineJoin: 'round',
                isArrowHead: true
            });
        }

        function getSmoothCurvePath(points) {
            if(points.length === 0) return '';
            if(points.length === 1) return `M ${points[0].x} ${points[0].y}`;
            if(points.length === 2) return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;
            
            let path = `M ${points[0].x} ${points[0].y}`;
            for (let i = 0; i < points.length - 1; i++) {
                let p0 = i > 0 ? points[i - 1] : points[0];
                let p1 = points[i];
                let p2 = points[i + 1];
                let p3 = i != points.length - 2 ? points[i + 2] : p2;

                let tension = 0.5;
                let cp1x = p1.x + (p2.x - p0.x) * tension / 3;
                let cp1y = p1.y + (p2.y - p0.y) * tension / 3;
                let cp2x = p2.x - (p3.x - p1.x) * tension / 3;
                let cp2y = p2.y - (p3.y - p1.y) * tension / 3;

                path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
            }
            return path;
        }

        // ==========================================
        // 8. 캔버스 마우스 조작 (정밀도 및 다중클릭 그리기 교정)
        // ==========================================
        
        canvas.on('text:editing:entered', (e) => { 
            window.scrollTo(0, 0); document.getElementById('workspace').scrollLeft = 0; document.getElementById('workspace').scrollTop = 0; 
            const obj = e.target;
            if (obj && obj.linkedShape) {
                document.getElementById('sub_toolbar').style.display = 'block';
                document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
                document.getElementById('panel_text').classList.add('active');
            } else if (!activeTool) {
                document.getElementById('sub_toolbar').style.display = 'block';
                document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
                document.getElementById('panel_text').classList.add('active');
            }
        });

        let lastTextEditExitTime = 0;
        canvas.on('text:editing:exited', (e) => { 
            lastTextEditExitTime = Date.now(); 
            canvas.discardActiveObject(); 
            canvas.requestRenderAll(); 
            
            const obj = e.target;
            if (obj && obj.linkedShape && activeTool === 'shape') {
                document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
                document.getElementById('panel_shape').classList.add('active');
            } else if (!activeTool) {
                document.getElementById('sub_toolbar').style.display = 'none';
                document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
            }
        });
        
        // ==========================================
        // ★ 펜 '일반' 모드 — 도형 자동 인식 엔진 (Shape Recognition)
        // ==========================================
        let _shapeRecogTimer = null;
        let _lastPenMoveTime = 0;
        let _isAutoShapeTriggered = false;

        // 마우스 정지 0.5초 감지: 드로잉 중 마우스가 멈추면 자동으로 mouseup 시뮬레이션
        canvas.on('mouse:move', function _penPauseDetector(o) {
            if (activeTool !== 'pen' || !canvas.isDrawingMode || !canvas._isCurrentlyDrawing) return;
            _lastPenMoveTime = Date.now();
            if (_shapeRecogTimer) clearTimeout(_shapeRecogTimer);
            _shapeRecogTimer = setTimeout(() => {
                if (!canvas._isCurrentlyDrawing || activeTool !== 'pen') return;
                _isAutoShapeTriggered = true; // 0.5초 일시정지에 의한 자동 인식 플래그 설정
                // 0.5초 동안 마우스가 움직이지 않았으므로 드로잉 자동 종료
                const upperCanvas = canvas.upperCanvasEl;
                if (upperCanvas) {
                    const lastEvt = new MouseEvent('mouseup', { bubbles: true, clientX: o.e.clientX, clientY: o.e.clientY });
                    upperCanvas.dispatchEvent(lastEvt);
                }
            }, 500);
        });

        // 마우스 뗄 때 타이머 정리
        canvas.on('mouse:up', function() {
            if (_shapeRecogTimer) { clearTimeout(_shapeRecogTimer); _shapeRecogTimer = null; }
        });

        // ── 도형 인식 핵심 알고리즘 ──
        function _extractPathPoints(pathObj) {
            const points = [];
            const path = pathObj.path;
            if (!path) return points;
            const po = pathObj.pathOffset || { x: 0, y: 0 };
            const m = pathObj.calcTransformMatrix();
            for (let i = 0; i < path.length; i++) {
                const cmd = path[i];
                if (cmd[0] === 'M' || cmd[0] === 'L') {
                    points.push(fabric.util.transformPoint({ x: cmd[1] - po.x, y: cmd[2] - po.y }, m));
                } else if (cmd[0] === 'Q') {
                    points.push(fabric.util.transformPoint({ x: cmd[3] - po.x, y: cmd[4] - po.y }, m));
                } else if (cmd[0] === 'C') {
                    points.push(fabric.util.transformPoint({ x: cmd[5] - po.x, y: cmd[6] - po.y }, m));
                }
            }
            return points;
        }

        function _getBoundingBox(pts) {
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            pts.forEach(p => { minX = Math.min(minX, p.x); minY = Math.min(minY, p.y); maxX = Math.max(maxX, p.x); maxY = Math.max(maxY, p.y); });
            return { minX, minY, maxX, maxY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2, w: maxX - minX, h: maxY - minY };
        }

        function _isClosedShape(pts) {
            if (pts.length < 5) return false;
            const d = Math.hypot(pts[0].x - pts[pts.length - 1].x, pts[0].y - pts[pts.length - 1].y);
            const bb = _getBoundingBox(pts);
            const diag = Math.hypot(bb.w, bb.h);
            return d < diag * 0.15;
        }

        function _getAngles(pts) {
            const angles = [];
            for (let i = 1; i < pts.length - 1; i++) {
                const a = Math.atan2(pts[i].y - pts[i - 1].y, pts[i].x - pts[i - 1].x);
                const b = Math.atan2(pts[i + 1].y - pts[i].y, pts[i + 1].x - pts[i].x);
                let diff = b - a;
                while (diff > Math.PI) diff -= 2 * Math.PI;
                while (diff < -Math.PI) diff += 2 * Math.PI;
                angles.push(diff);
            }
            return angles;
        }

        function _detectCorners(pts) {
            // 점을 균등 간격으로 리샘플링한 후 급격한 방향 변화 감지
            const resampled = _resample(pts, 64);
            const corners = [0];
            const threshold = Math.PI / 4; // 45도 이상 꺾이면 코너
            for (let i = 2; i < resampled.length - 2; i++) {
                const v1x = resampled[i].x - resampled[i - 2].x;
                const v1y = resampled[i].y - resampled[i - 2].y;
                const v2x = resampled[i + 2].x - resampled[i].x;
                const v2y = resampled[i + 2].y - resampled[i].y;
                const dot = v1x * v2x + v1y * v2y;
                const mag1 = Math.hypot(v1x, v1y);
                const mag2 = Math.hypot(v2x, v2y);
                if (mag1 < 1 || mag2 < 1) continue;
                const angle = Math.acos(Math.max(-1, Math.min(1, dot / (mag1 * mag2))));
                if (angle > threshold) corners.push(i);
            }
            corners.push(resampled.length - 1);
            // 너무 가까운 코너 합침
            const merged = [corners[0]];
            for (let i = 1; i < corners.length; i++) {
                if (corners[i] - merged[merged.length - 1] > 3) merged.push(corners[i]);
            }
            return merged.map(i => resampled[i]);
        }

        function _resample(pts, n) {
            if (pts.length < 2) return pts.slice();
            let totalLen = 0;
            for (let i = 1; i < pts.length; i++) totalLen += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
            const interval = totalLen / (n - 1);
            const result = [{ x: pts[0].x, y: pts[0].y }];
            let dist = 0;
            for (let i = 1; i < pts.length; i++) {
                const d = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
                while (dist + d >= interval && result.length < n) {
                    const t = (interval - dist) / d;
                    result.push({ x: pts[i - 1].x + t * (pts[i].x - pts[i - 1].x), y: pts[i - 1].y + t * (pts[i].y - pts[i - 1].y) });
                    pts = [result[result.length - 1], ...pts.slice(i)];
                    i = 1;
                    dist = 0;
                    break;
                }
                if (result.length >= n) break;
                dist += d;
            }
            while (result.length < n) result.push({ x: pts[pts.length - 1].x, y: pts[pts.length - 1].y });
            return result;
        }

        function _circularityScore(pts, cx, cy) {
            const dists = pts.map(p => Math.hypot(p.x - cx, p.y - cy));
            const avgR = dists.reduce((s, d) => s + d, 0) / dists.length;
            if (avgR < 5) return 0;
            const variance = dists.reduce((s, d) => s + (d - avgR) ** 2, 0) / dists.length;
            return 1 - Math.sqrt(variance) / avgR;
        }

        function _simplifyDP(pts, epsilon) {
            if (pts.length <= 2) return pts;
            let maxDist = 0; let index = 0;
            const end = pts.length - 1;
            for (let i = 1; i < end; i++) {
                const a = pts[0], b = pts[end], p = pts[i];
                const num = Math.abs((b.y - a.y) * p.x - (b.x - a.x) * p.y + b.x * a.y - b.y * a.x);
                const den = Math.hypot(b.y - a.y, b.x - a.x);
                const d = den === 0 ? Math.hypot(p.x - a.x, p.y - a.y) : num / den;
                if (d > maxDist) { maxDist = d; index = i; }
            }
            if (maxDist > epsilon) {
                const left = _simplifyDP(pts.slice(0, index + 1), epsilon);
                const right = _simplifyDP(pts.slice(index), epsilon);
                return left.slice(0, left.length - 1).concat(right);
            } else {
                return [pts[0], pts[end]];
            }
        }

        function _recognizeShape(pts) {
            if (pts.length < 8) return null;
            const bb = _getBoundingBox(pts);
            const closed = _isClosedShape(pts);
            const diag = Math.hypot(bb.w, bb.h);
            if (diag < 15) return null;

            // === 0. 한붓그리기 별(펜타그램) 인식 ===
            const pentaResult = _pentagramScore(pts, bb);
            if (pentaResult && pentaResult.score > 0.55) {
                return { type: 'star', cx: bb.cx, cy: bb.cy, outerR: pentaResult.outerR, innerR: pentaResult.outerR * 0.38, points: 5 };
            }

            // === 1. 닫힌 도형 인식 ===
            if (closed) {
                const cx = bb.cx, cy = bb.cy;
                const circ = _circularityScore(pts, cx, cy);
                if (circ > 0.85) {
                    const ratio = bb.w / bb.h;
                    if (ratio > 0.75 && ratio < 1.33) return { type: 'circle', cx, cy, r: Math.max(bb.w, bb.h) / 2 };
                    else return { type: 'ellipse', cx, cy, rx: bb.w / 2, ry: bb.h / 2 };
                }

                // DP 단순화로 사용자가 그린 형태 정확히 유지 (에러허용: 대각선의 4.5%)
                let closedPts = pts.slice();
                closedPts.push(pts[0]);
                const dp = _simplifyDP(closedPts, diag * 0.045);
                const n = dp.length - 1;

                if (n === 3) return { type: 'triangle', corners: dp.slice(0, -1) };
                if (n === 4) return { type: 'rect', corners: dp.slice(0, -1) };
                if (n === 5) return { type: 'pentagon', cx, cy, r: Math.max(bb.w, bb.h) / 2 };
                if (n === 6) return { type: 'hexagon', cx, cy, r: Math.max(bb.w, bb.h) / 2 };

                // 반원/부채꼴 감지 (DP 결과 선분 길이 분석)
                let segs = [];
                let perimeter = 0;
                for (let i = 0; i < n; i++) {
                    const len = Math.hypot(dp[i+1].x - dp[i].x, dp[i+1].y - dp[i].y);
                    segs.push({ len, i });
                    perimeter += len;
                }
                segs.sort((a, b) => b.len - a.len);

                if (n >= 3) {
                    // 부채꼴: 2개의 가장 긴 선분이 인접하고 전체 둘레의 40% 이상 차지
                    if (segs.length >= 2 && (segs[0].len + segs[1].len) / perimeter > 0.40) {
                        const i1 = segs[0].i, i2 = segs[1].i;
                        if (Math.abs(i1 - i2) === 1 || Math.abs(i1 - i2) === n - 1) {
                            let center, p1, p2;
                            if ((i1 + 1) % n === i2) { center = dp[i2]; p1 = dp[i1]; p2 = dp[i2+1]; }
                            else if ((i2 + 1) % n === i1) { center = dp[i1]; p1 = dp[i2]; p2 = dp[i1+1]; }
                            else if (i1 === 0 && i2 === n - 1) { center = dp[0]; p1 = dp[1]; p2 = dp[n-1]; }
                            else if (i2 === 0 && i1 === n - 1) { center = dp[0]; p1 = dp[n-1]; p2 = dp[1]; }
                            
                            const r = (segs[0].len + segs[1].len) / 2;
                            let startAngle = Math.atan2(p1.y - center.y, p1.x - center.x);
                            let endAngle = Math.atan2(p2.y - center.y, p2.x - center.x);
                            let dAngle = endAngle - startAngle;
                            if (dAngle > Math.PI) dAngle -= 2 * Math.PI;
                            if (dAngle < -Math.PI) dAngle += 2 * Math.PI;
                            endAngle = startAngle + dAngle;
                            return { type: 'sector', cx: center.x, cy: center.y, r, startAngle, endAngle };
                        }
                    }
                    
                    // 반원: 1개의 가장 긴 선분(지름)이 전체 둘레의 28% 이상 차지
                    if (segs[0].len / perimeter > 0.28) {
                        const idx = segs[0].i;
                        const p1 = dp[idx], p2 = dp[idx+1];
                        const cx = (p1.x + p2.x) / 2, cy = (p1.y + p2.y) / 2;
                        const r = segs[0].len / 2;
                        const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
                        let crossSum = 0;
                        for(let p of pts) {
                            crossSum += (p2.x - p1.x) * (p.y - p1.y) - (p2.y - p1.y) * (p.x - p1.x);
                        }
                        const isClockwise = crossSum > 0;
                        let startAngle = angle + (isClockwise ? 0 : Math.PI);
                        let endAngle = startAngle + Math.PI;
                        return { type: 'semicircle', cx, cy, r, startAngle, endAngle };
                    }
                }

                // 하트는 코너 감지로 유지
                const corners = _detectCorners(pts);
                if (corners.length >= 3 && corners.length <= 6) {
                    if (_heartScore(pts, bb) > 0.7) return { type: 'heart', cx, cy, w: bb.w, h: bb.h };
                }
                
                if (circ > 0.7) return { type: 'ellipse', cx, cy, rx: bb.w / 2, ry: bb.h / 2 };

                // 매칭 안되면 초월/다항함수처럼 매끈한 곡선 생성 (DP 극단적 단순화 후 곡선화)
                const dpCurve = _simplifyDP(pts, diag * 0.08);
                return { type: 'curve', points: dpCurve };
            }

            // === 2. 열린 도형 ===
            if (!closed) {
                // 열린 도형은 초월/다항함수처럼 매끈한 곡선(curve)으로 변환
                const dpCurve = _simplifyDP(pts, diag * 0.08);
                return { type: 'curve', points: dpCurve };
            }

            return null;
        }

        // ── 한붓그리기 별(펜타그램 ☆) 전용 인식 ──
        function _pentagramScore(pts, bb) {
            // 코너를 감지하고 정확히 5개의 뾰족한 꼭짓점이 있는지 확인
            const corners = _detectCorners(pts);
            if (corners.length < 5 || corners.length > 12) return { score: 0 };

            const cx = bb.cx, cy = bb.cy;
            // 중심에서 가장 먼 5개 점을 별의 꼭짓점 후보로 선택
            const sorted = corners.slice().sort((a, b) => Math.hypot(b.x - cx, b.y - cy) - Math.hypot(a.x - cx, a.y - cy));
            const tips = sorted.slice(0, 5);
            if (tips.length < 5) return { score: 0 };

            // 5개 꼭짓점의 각도를 계산하고 균등 분포(72°간격) 여부 확인
            const angles = tips.map(p => Math.atan2(p.y - cy, p.x - cx)).sort((a, b) => a - b);
            let gapScore = 0;
            const idealGap = (2 * Math.PI) / 5; // 72°
            for (let i = 0; i < 5; i++) {
                let gap = angles[(i + 1) % 5] - angles[i];
                if (gap < 0) gap += 2 * Math.PI;
                gapScore += 1 - Math.min(1, Math.abs(gap - idealGap) / idealGap);
            }
            gapScore /= 5;

            // 5개 꼭짓점의 중심 거리 균등성
            const tipDists = tips.map(p => Math.hypot(p.x - cx, p.y - cy));
            const avgR = tipDists.reduce((s, d) => s + d, 0) / tipDists.length;
            const distVariance = tipDists.reduce((s, d) => s + (d - avgR) ** 2, 0) / tipDists.length;
            const distScore = Math.max(0, 1 - Math.sqrt(distVariance) / avgR);

            // 경로에 교차(self-intersection)가 있는지 확인 — 별 모양의 핵심 특징
            const crossings = _countSelfIntersections(pts);
            if (crossings < 1) return { score: 0 }; // 펜타그램(한붓그리기 별)은 반드시 교차점이 있어야 함
            const crossScore = crossings >= 3 ? 1 : crossings >= 1 ? 0.5 : 0;

            const score = gapScore * 0.4 + distScore * 0.3 + crossScore * 0.3;
            return { score, outerR: avgR };
        }

        function _countSelfIntersections(pts) {
            // 선분 교차 횟수를 세기 위해 간격을 두고 샘플링
            const step = Math.max(1, Math.floor(pts.length / 30));
            const segs = [];
            for (let i = 0; i < pts.length - step; i += step) {
                segs.push([pts[i], pts[Math.min(i + step, pts.length - 1)]]);
            }
            let count = 0;
            for (let i = 0; i < segs.length; i++) {
                for (let j = i + 2; j < segs.length; j++) {
                    if (_segmentsIntersect(segs[i][0], segs[i][1], segs[j][0], segs[j][1])) count++;
                }
            }
            return count;
        }

        function _segmentsIntersect(a, b, c, d) {
            const cross = (o, p, q) => (p.x - o.x) * (q.y - o.y) - (p.y - o.y) * (q.x - o.x);
            const d1 = cross(c, d, a), d2 = cross(c, d, b);
            const d3 = cross(a, b, c), d4 = cross(a, b, d);
            if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return true;
            return false;
        }

        function _heartScore(pts, bb) {
            const cx = bb.cx, cy = bb.cy;
            // 하트는 위쪽 절반에 좌우 대칭적인 2개의 볼록한 영역, 아래쪽에 뾰족한 꼭짓점
            let bottomPt = pts[0], topLeftPt = null, topRightPt = null;
            pts.forEach(p => { if (p.y > bottomPt.y) bottomPt = p; });

            const topHalf = pts.filter(p => p.y < cy);
            const leftTop = topHalf.filter(p => p.x < cx);
            const rightTop = topHalf.filter(p => p.x >= cx);

            if (leftTop.length < 3 || rightTop.length < 3) return 0;

            topLeftPt = leftTop.reduce((best, p) => p.y < best.y ? p : best, leftTop[0]);
            topRightPt = rightTop.reduce((best, p) => p.y < best.y ? p : best, rightTop[0]);

            // 아래 꼭짓점이 중앙 하단에 있어야 함
            const bottomCentered = Math.abs(bottomPt.x - cx) < bb.w * 0.25;
            const bottomIsLowest = bottomPt.y > cy + bb.h * 0.2;
            // 위쪽에 2개의 봉우리가 있어야 함
            const hasTwoBumps = topLeftPt.y < cy - bb.h * 0.1 && topRightPt.y < cy - bb.h * 0.1;
            // 상단 중앙에 오목한 부분이 있어야 함
            const midTopPts = topHalf.filter(p => Math.abs(p.x - cx) < bb.w * 0.15);
            const midTopY = midTopPts.length > 0 ? Math.min(...midTopPts.map(p => p.y)) : bb.minY;
            const hasIndent = midTopY > Math.min(topLeftPt.y, topRightPt.y) + bb.h * 0.05;

            let score = 0;
            if (bottomCentered) score += 0.25;
            if (bottomIsLowest) score += 0.25;
            if (hasTwoBumps) score += 0.25;
            if (hasIndent) score += 0.25;
            return score;
        }




        function _simplifyToN(corners, n) {
            if (corners.length <= n) return corners;
            // 가장 먼 n개 코너 선택
            while (corners.length > n) {
                let minDist = Infinity, minIdx = 1;
                for (let i = 1; i < corners.length - 1; i++) {
                    const d = Math.hypot(corners[i].x - corners[i - 1].x, corners[i].y - corners[i - 1].y);
                    if (d < minDist) { minDist = d; minIdx = i; }
                }
                corners.splice(minIdx, 1);
            }
            return corners;
        }

        function _rectangularityScore(corners4, bb) {
            if (corners4.length !== 4) return 0;
            // 4개 코너가 bb의 꼭짓점에 가까운 정도 측정
            const bbCorners = [
                { x: bb.minX, y: bb.minY }, { x: bb.maxX, y: bb.minY },
                { x: bb.maxX, y: bb.maxY }, { x: bb.minX, y: bb.maxY }
            ];
            let totalDist = 0;
            const diag = Math.hypot(bb.w, bb.h);
            corners4.forEach(c => {
                const minD = Math.min(...bbCorners.map(bc => Math.hypot(c.x - bc.x, c.y - bc.y)));
                totalDist += minD;
            });
            return Math.max(0, 1 - totalDist / (diag * 2));
        }

        function _arcScore(pts) {
            // 3점 원 피팅으로 호 인식
            const p1 = pts[0], p2 = pts[Math.floor(pts.length / 2)], p3 = pts[pts.length - 1];
            const ax = p1.x, ay = p1.y, bx = p2.x, by = p2.y, ex = p3.x, ey = p3.y;
            const D = 2 * (ax * (by - ey) + bx * (ey - ay) + ex * (ay - by));
            if (Math.abs(D) < 1) return null;
            const cx = ((ax * ax + ay * ay) * (by - ey) + (bx * bx + by * by) * (ey - ay) + (ex * ex + ey * ey) * (ay - by)) / D;
            const cy = ((ax * ax + ay * ay) * (ex - bx) + (bx * bx + by * by) * (ax - ex) + (ex * ex + ey * ey) * (bx - ax)) / D;
            const r = Math.hypot(p1.x - cx, p1.y - cy);
            if (r < 10 || r > 5000) return null;
            const dists = pts.map(p => Math.abs(Math.hypot(p.x - cx, p.y - cy) - r));
            const avgError = dists.reduce((s, d) => s + d, 0) / dists.length;
            const score = Math.max(0, 1 - avgError / r);
            const startAngle = Math.atan2(p1.y - cy, p1.x - cx);
            const endAngle = Math.atan2(p3.y - cy, p3.x - cx);
            return { score, cx, cy, r, startAngle, endAngle };
        }

        // ── 인식된 도형을 Fabric 개체로 변환 ──
        function _createRecognizedShape(shape, strokeColor, strokeWidth, strokeDashArray) {
            const opts = { stroke: strokeColor, strokeWidth: strokeWidth, strokeDashArray: strokeDashArray, fill: 'transparent', selectable: true, isTemp: false, strokeLineJoin: 'round', strokeLineCap: 'round' };

            switch (shape.type) {
                case 'circle':
                    return new fabric.Circle({ ...opts, left: shape.cx - shape.r, top: shape.cy - shape.r, radius: shape.r });
                case 'ellipse':
                    return new fabric.Ellipse({ ...opts, left: shape.cx, top: shape.cy, rx: shape.rx, ry: shape.ry, originX: 'center', originY: 'center' });
                case 'triangle':
                case 'rect':
                case 'polygon': {
                    const polyPts = shape.corners.map(c => ({ x: c.x, y: c.y }));
                    return new fabric.Polygon(polyPts, { ...opts });
                }
                case 'pentagon': {
                    const penPts = [];
                    for (let i = 0; i < 5; i++) {
                        const angle = -Math.PI / 2 + (i * 2 * Math.PI) / 5;
                        penPts.push({ x: shape.cx + shape.r * Math.cos(angle), y: shape.cy + shape.r * Math.sin(angle) });
                    }
                    return new fabric.Polygon(penPts, { ...opts });
                }
                case 'hexagon': {
                    const hexPts = [];
                    for (let i = 0; i < 6; i++) {
                        const angle = -Math.PI / 2 + (i * 2 * Math.PI) / 6;
                        hexPts.push({ x: shape.cx + shape.r * Math.cos(angle), y: shape.cy + shape.r * Math.sin(angle) });
                    }
                    return new fabric.Polygon(hexPts, { ...opts });
                }
                case 'star': {
                    const starPts = [];
                    const n = shape.points || 5;
                    const startA = -Math.PI / 2;
                    for (let i = 0; i < n * 2; i++) {
                        const angle = startA + (i * Math.PI) / n;
                        const r = i % 2 === 0 ? shape.outerR : shape.innerR;
                        starPts.push({ x: shape.cx + r * Math.cos(angle), y: shape.cy + r * Math.sin(angle) });
                    }
                    return new fabric.Polygon(starPts, { ...opts });
                }
                case 'heart': {
                    const hw = shape.w / 2, hh = shape.h / 2;
                    const hcx = shape.cx, hcy = shape.cy;
                    const heartPath = `M ${hcx} ${hcy + hh} ` +
                        `C ${hcx - hw * 1.2} ${hcy + hh * 0.1}, ${hcx - hw * 0.8} ${hcy - hh * 0.8}, ${hcx} ${hcy - hh * 0.3} ` +
                        `C ${hcx + hw * 0.8} ${hcy - hh * 0.8}, ${hcx + hw * 1.2} ${hcy + hh * 0.1}, ${hcx} ${hcy + hh} Z`;
                    return new fabric.Path(heartPath, { ...opts });
                }
                case 'semicircle': {
                    const segments = 50;
                    let sa = shape.startAngle, ea = shape.endAngle;
                    let diff = ea - sa;
                    if (diff > Math.PI) diff -= 2 * Math.PI;
                    if (diff < -Math.PI) diff += 2 * Math.PI;
                    let pathStr = '';
                    for (let i = 0; i <= segments; i++) {
                        const t = sa + diff * (i / segments);
                        const x = shape.cx + shape.r * Math.cos(t);
                        const y = shape.cy + shape.r * Math.sin(t);
                        pathStr += (i === 0 ? 'M' : 'L') + ` ${x} ${y} `;
                    }
                    pathStr += 'Z';
                    return new fabric.Path(pathStr, { ...opts });
                }
                case 'sector': {
                    const segs = 50;
                    let sa2 = shape.startAngle, ea2 = shape.endAngle;
                    let diff2 = ea2 - sa2;
                    if (diff2 > Math.PI) diff2 -= 2 * Math.PI;
                    if (diff2 < -Math.PI) diff2 += 2 * Math.PI;
                    let pStr = `M ${shape.cx} ${shape.cy} `;
                    for (let i = 0; i <= segs; i++) {
                        const t = sa2 + diff2 * (i / segs);
                        const x = shape.cx + shape.r * Math.cos(t);
                        const y = shape.cy + shape.r * Math.sin(t);
                        pStr += `L ${x} ${y} `;
                    }
                    pStr += 'Z';
                    return new fabric.Path(pStr, { ...opts });
                }
                case 'curve': {
                    return new fabric.Path(getSmoothCurvePath(shape.points), { ...opts });
                }
                default:
                    return null;
            }
        }

        // ── 인식 성공 시 화면에 간단한 알림 표시 ──
        function _showShapeRecogNotice(typeName) {
            let notice = document.getElementById('shape_recog_notice');
            if (!notice) {
                notice = document.createElement('div');
                notice.id = 'shape_recog_notice';
                notice.style.cssText = 'position:fixed;top:70px;left:50%;transform:translateX(-50%);background:rgba(30,30,30,0.85);color:#fff;padding:6px 16px;border-radius:8px;font-size:13px;z-index:9999;pointer-events:none;opacity:0;transition:opacity 0.3s;font-family:Pretendard,sans-serif;';
                document.body.appendChild(notice);
            }
            const names = { circle: '원', ellipse: '타원', rect: '사각형', polygon: '다각형', star: '별', heart: '하트', pentagon: '오각형', hexagon: '육각형', semicircle: '반원', sector: '부채꼴', triangle: '삼각형', curve: '부드러운 곡선' };
            notice.textContent = `✨ ${names[typeName] || typeName} 도형으로 변환됨`;
            notice.style.opacity = '1';
            clearTimeout(notice._timer);
            notice._timer = setTimeout(() => { notice.style.opacity = '0'; }, 1500);
        }

        canvas.on('path:created', (e) => {
            if (activeTool === 'pen') {
                const isAuto = _isAutoShapeTriggered;
                _isAutoShapeTriggered = false; // 플래그 초기화
                
                if (!isAuto) {
                    // 일반 펜 선인 경우 개별 개체로 인식 및 히스토리 저장
                    e.path.set({ selectable: true, isTemp: false, objectCaching: true });
                    updateObjectSelectability();
                    saveHistory();
                    return; 
                }

                const pathObj = e.path;
                const pts = _extractPathPoints(pathObj);
                const recognized = _recognizeShape(pts);

                if (recognized) {
                    // 원래 path의 스타일 정보 추출
                    const sColor = pathObj.stroke;
                    const sWidth = pathObj.strokeWidth;
                    const sDash = pathObj.strokeDashArray;

                    // 인식된 도형 생성
                    const newObj = _createRecognizedShape(recognized, sColor, sWidth, sDash);
                    if (newObj) {
                        canvas.remove(pathObj);
                        canvas.add(newObj);
                        canvas.setActiveObject(newObj);
                        _showShapeRecogNotice(recognized.type);
                        updateObjectSelectability();
                        saveHistory();
                        canvas.requestRenderAll();
                        return;
                    }
                }

                // 인식 실패 시 기존 동작 유지
                pathObj.set({ selectable: true, isTemp: false });
                updateObjectSelectability();
                saveHistory();
            }
        });

        let multiClickDrawing = false;
        let clickPoints = [];
        const floatingTooltip = document.getElementById('floating_tooltip');

        function finalizeMultiClickDrawing() {
            if(!multiClickDrawing) return;
            multiClickDrawing = false;
            floatingTooltip.style.display = 'none';
            
            // 종료점(ESC/더블클릭) 마우스 오프셋 보정 및 확정
            let uniquePoints = [clickPoints[0]];
            for(let i=1; i<clickPoints.length - 1; i++) {
                if(Math.hypot(clickPoints[i].x - uniquePoints[uniquePoints.length-1].x, clickPoints[i].y - uniquePoints[uniquePoints.length-1].y) > 2) {
                    uniquePoints.push(clickPoints[i]);
                }
            }
            let lastPt = clickPoints[clickPoints.length - 1];
            if (Math.hypot(lastPt.x - uniquePoints[uniquePoints.length-1].x, lastPt.y - uniquePoints[uniquePoints.length-1].y) > 2) {
                uniquePoints.push(lastPt);
            } else {
                uniquePoints[uniquePoints.length-1] = lastPt; // 현재 커서 위치로 덮어씌움
            }
            clickPoints = uniquePoints;
            
            if(clickPoints.length < 2) {
                if(currentShape) canvas.remove(currentShape);
                if(arrowHead) canvas.remove(arrowHead);
                currentShape = null; arrowHead = null;
                return;
            }
            
            if(currentShape) {
                const lineRadio = document.querySelector('input[name="line_type"]:checked');
                const isCurve = lineRadio && lineRadio.value === 'curve';
                const weight = parseInt(document.getElementById('shape_weight').value);

                let p2 = clickPoints[clickPoints.length - 1];
                let p1 = clickPoints[clickPoints.length - 2];
                for(let i = clickPoints.length - 2; i >= 0; i--) {
                    if(Math.hypot(clickPoints[i].x - p2.x, clickPoints[i].y - p2.y) > 3) {
                        p1 = clickPoints[i];
                        break;
                    }
                }
                let angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
                let renderPoints = [...clickPoints];

                if(arrowHead) {
                    const sizeMult = sysArrowSize === 'xs' ? 1.5 : sysArrowSize === 's' ? 2 : sysArrowSize === 'l' ? 4 : 3;
                    const w = weight * sizeMult + 8;
                    let pullBack = (sysArrowType === 'stealth') ? w * 0.6 : (sysArrowType === 'open') ? 0 : w;
                    
                    let lineEndX = p2.x - Math.cos(angle) * pullBack;
                    let lineEndY = p2.y - Math.sin(angle) * pullBack;
                    renderPoints[renderPoints.length - 1] = {x: lineEndX, y: lineEndY};
                    
                    let newPathStr = isCurve ? getSmoothCurvePath(renderPoints) : renderPoints.reduce((acc, pt, idx) => acc + (idx===0?'M':'L') + ` ${pt.x} ${pt.y} `, '');
                    currentShape.set({ path: new fabric.Path(newPathStr).path });
                    
                    canvas.remove(arrowHead);
                    arrowHead = createArrowHead(p2.x, p2.y, angle, sysArrowType, sysArrowSize, strokeColor, weight);
                    canvas.add(arrowHead);
                    
                    currentShape.arrowType = sysArrowType;
                    currentShape.arrowSize = sysArrowSize;
                    const group = new fabric.Group([currentShape, arrowHead], {selectable: true});
                    group.arrowType = sysArrowType;
                    group.arrowSize = sysArrowSize;
                    canvas.remove(currentShape, arrowHead);
                    canvas.add(group);
                } else {
                    let newPathStr = isCurve ? getSmoothCurvePath(renderPoints) : renderPoints.reduce((acc, pt, idx) => acc + (idx===0?'M':'L') + ` ${pt.x} ${pt.y} `, '');
                    currentShape.set({ path: new fabric.Path(newPathStr).path, selectable: true, isTemp: false });
                }
            }
            currentShape = null; arrowHead = null; clickPoints = [];
            updateObjectSelectability();
            canvas.requestRenderAll(); saveHistory(); deactivateActiveTool(); deactivateActiveTool();
        }

        let lastMouseDownPoint = null;
        let _lastActiveShapeForLinkedText = null;
        canvas.on('selection:created', e => { if (e.selected) e.selected.forEach(obj => { obj.__selectedThisClick = true; }); });
        canvas.on('selection:updated', e => { if (e.selected) e.selected.forEach(obj => { obj.__selectedThisClick = true; }); });

        canvas.on('mouse:down', o => {
            if (document.getElementById('emoji_popup').style.display === 'block') { document.getElementById('emoji_popup').style.display = 'none'; return; }
            const pointer = canvas.getPointer(o.e);
            lastMouseDownPoint = pointer;
            
            // 붙여넣기 좌표 갱신
            lastCanvasClick = { x: pointer.x, y: pointer.y };

            // === 텍스트 편집 모드 보호 및 드래그 선택 강화 ===
            if (!activeTool && o.target) {
                let editingText = null;
                if (o.target.isEditing) editingText = o.target;
                else if (o.target.linkedText && o.target.linkedText.isEditing) editingText = o.target.linkedText;
                
                if (editingText) {
                    canvas._currentTransform = null; // 이동 방지 (4방향 커서 방지)
                    if (canvas.getActiveObject() !== editingText) {
                        canvas.setActiveObject(editingText);
                    }
                    if (o.target !== editingText) {
                        // 도형의 빈 공간을 클릭한 경우, 텍스트 객체에 직접 마우스 이벤트를 전달한 효과를 줌
                        if (typeof editingText.setCursorByClick === 'function') {
                            try { editingText.setCursorByClick(o.e); } catch(e) {}
                        }
                        if (typeof editingText.initMouseMoveHandler === 'function') {
                            try { editingText.initMouseMoveHandler(o.e); } catch(e) {}
                        }
                    }
                    return;
                }
            }
            
            // 도형 내 글상자: 첫 클릭은 도형 선택, 두 번째 클릭은 텍스트 편집
            const isControl = canvas._currentTransform && canvas._currentTransform.action && canvas._currentTransform.action !== 'drag';
            if (!activeTool && o.target && o.target.linkedShape && !isControl) {
                // 클릭 대상이 텍스트 오브젝트인 경우
                const shape = o.target.linkedShape;
                if (_lastActiveShapeForLinkedText === shape) {
                    // 두 번째 클릭: 텍스트 편집 모드 직접 진입
                    _lastActiveShapeForLinkedText = null;
                    const textTarget = o.target;
                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    canvas._currentTransform = null;
                    canvas.requestRenderAll();
                    return;
                } else {
                    // 첫 번째 클릭: 도형 선택으로 리다이렉트
                    o.target.__shapeJustSelected = true;
                    _lastActiveShapeForLinkedText = shape;
                    canvas.setActiveObject(shape);
                    canvas.requestRenderAll();
                    return;
                }
            } else if (!activeTool && o.target && o.target.linkedText && !isControl) {
                // 클릭 대상이 도형 자체인 경우 (선택 핸들이 텍스트를 덮어서 도형이 타겟이 됨)
                const shape = o.target;
                const textTarget = shape.linkedText;
                if (_lastActiveShapeForLinkedText === shape) {
                    // 두 번째 클릭: 텍스트 편집 모드 진입
                    _lastActiveShapeForLinkedText = null;
                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    canvas._currentTransform = null;
                    canvas.requestRenderAll();
                    return;
                } else {
                    // 첫 번째 클릭 또는 일반 도형 클릭
                    _lastActiveShapeForLinkedText = shape;
                }
            } else {
                // 다른 곳 클릭 시 리셋
                _lastActiveShapeForLinkedText = null;
            }

            if (activeTool === 'text') {
                if (Date.now() - lastTextEditExitTime < 200) return; 
                const activeObj = canvas.getActiveObject();
                if (activeObj && activeObj.isEditing) { canvas.discardActiveObject(); canvas.requestRenderAll(); return; }
                if (o.target && (o.target.type === 'i-text' || o.target.type === 'text' || o.target.type === 'textbox')) return;
                
                const fColor = getTextBgOpacity();
                const scaledSize = parseInt(document.getElementById('text_size_input').value);
                const textAlignVal = document.getElementById('text_align').value;
                currentShape = new fabric.Textbox('', {
                    left: pointer.x, top: pointer.y, fontSize: scaledSize,
                    cursorWidth: 2, cursorColor: textColor, textAlign: textAlignVal,
                    fill: textColor, backgroundColor: fColor, fontWeight: txtB ? 'bold' : 'normal', fontStyle: txtI ? 'italic' : 'normal', underline: txtU, fontFamily: 'Pretendard',
                    originX: 'left', originY: 'top', splitByGrapheme: true, isWidthFixed: false
                }); 
                currentShape.on('changed', function() {
                    if (!this.isWidthFixed) {
                        const ctx = this.canvas.getContext();
                        ctx.font = (this.fontStyle || 'normal') + ' ' + (this.fontWeight || 'normal') + ' ' + this.fontSize + 'px ' + this.fontFamily;
                        let maxW = 50;
                        const lines = this.text.split('\n');
                        for (let i=0; i<lines.length; i++) {
                            const w = ctx.measureText(lines[i]).width;
                            if (w > maxW) maxW = w;
                        }
                        this.set({ width: maxW + 10 });
                    }
                });
                currentShape.on('resizing', function() { this.isWidthFixed = true; });
                currentShape.on('scaling', function() { this.isWidthFixed = true; });
                
                currentShape.isTemp = true; canvas.add(currentShape); canvas.setActiveObject(currentShape); currentShape.enterEditing(); return;
            }

            if (activeTool === 'eraser') { 
                const target = canvas.findTarget(o.e, false);
                if (target && target.evented) { canvas.remove(target); canvas.requestRenderAll(); saveHistory(); }
                return; 
            }

            if (activeTool === 'pen' && document.querySelector('input[name="pen_mode"]:checked').value === 'straight') {
                isDrawing = true; origX = pointer.x; origY = pointer.y;
                const weight = parseInt(document.getElementById('pen_weight').value) || 5;
                const isDashed = document.getElementById('pen_dashed').checked;
                const dashArr = isDashed ? [weight * 3, weight * 3] : null;

                currentShape = new fabric.Path(`M ${origX} ${origY} L ${origX} ${origY}`, {
                    fill: 'transparent', stroke: penCurrentColor, strokeWidth: weight,
                    strokeDashArray: dashArr, strokeLineCap: 'round', strokeLineJoin: 'round',
                    selectable: false, isTemp: true, objectCaching: false
                });
                canvas.add(currentShape);
                return;
            }

            // 도구가 활성화되어 있지 않고 대상이 있다면 (선택 이동 & 맨 앞으로 가져오기)
            if (!activeTool && o.target && o.target.selectable) {
                // 텍스트 편집 중에는 Fabric.js 내장 IText 핸들러에 완전히 위임 (드래그 블록지정, 커서 이동 등)
                if (o.target.isEditing) return;
                
                if (o.target._skipBringToFront) {
                    delete o.target._skipBringToFront;
                } else if (canvas.getActiveObject() !== o.target) {
                    if (o.target.linkedText) {
                        canvas.bringToFront(o.target);
                        canvas.bringToFront(o.target.linkedText);
                    } else if (o.target.linkedShape) {
                        canvas.bringToFront(o.target.linkedShape);
                        canvas.bringToFront(o.target);
                    } else {
                        canvas.bringToFront(o.target);
                    }
                }
                saveHistory();
                return;
            }

            const shapeType = document.getElementById('shape_type').value;
            const lineRadio = document.querySelector('input[name="line_type"]:checked');
            const isLineShape = (shapeType === 'line' || shapeType === 'arrow');

            if (isLineShape && activeTool === 'shape') {
                floatingTooltip.style.display = 'block';
                if (!multiClickDrawing) {
                    multiClickDrawing = true;
                    clickPoints = [{x: pointer.x, y: pointer.y}, {x: pointer.x, y: pointer.y}];
                    
                    const weight = parseInt(document.getElementById('shape_weight').value);
                    const isDashed = document.getElementById('chk_dashed') && document.getElementById('chk_dashed').checked;
                    const dashArr = isDashed ? [weight * 3, weight * 3] : null;

                    if(lineRadio && lineRadio.value === 'curve') {
                        currentShape = new fabric.Path(getSmoothCurvePath(clickPoints), { fill: 'transparent', stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, isTemp: true, isArrowBody: true });
                    } else {
                        currentShape = new fabric.Path(`M ${clickPoints[0].x} ${clickPoints[0].y} L ${clickPoints[1].x} ${clickPoints[1].y}`, { fill: 'transparent', stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, strokeLineJoin: 'round', isTemp: true, isArrowBody: true });
                    }
                    canvas.add(currentShape);
                    if (shapeType === 'arrow') { 
                        arrowHead = createArrowHead(pointer.x, pointer.y, 0, sysArrowType, sysArrowSize, strokeColor, weight); 
                        canvas.add(arrowHead); 
                    }
                } else {
                    if (!lineRadio || lineRadio.value !== 'normal') {
                        clickPoints[clickPoints.length - 1] = {x: pointer.x, y: pointer.y};
                        clickPoints.push({x: pointer.x, y: pointer.y});
                    }
                }
                return;
            }

            if (['shape', 'emoji', 'image', 'crop', 'mosaic'].includes(activeTool)) {
                isDrawing = true; origX = pointer.x; origY = pointer.y;

                if (activeTool === 'crop') { capStartX = o.e.clientX; capStartY = o.e.clientY;
                } else if (activeTool === 'mosaic') {
                    currentShape = new fabric.Rect({ left: origX, top: origY, width: 0, height: 0, fill: 'rgba(0,0,0,0.0)', stroke: '#3b82f6', strokeDashArray: [5, 5], selectable: false, isTemp: true }); canvas.add(currentShape);
                } else if (activeTool === 'emoji') {
                    if (!selectedEmoji && !selectedEmojiUrl) return customAlert("이모티콘을 먼저 선택해주세요.");
                    const scaledSize = parseInt(document.getElementById('text_size_input').value) || 36;
                    
                    if (selectedEmojiUrl) {
                        const customHtmlImg = new Image();
                        customHtmlImg.onload = function() {
                            const tempCanvas = document.createElement('canvas');
                            tempCanvas.width = customHtmlImg.width;
                            tempCanvas.height = customHtmlImg.height;
                            const ctx = tempCanvas.getContext('2d', { willReadFrequently: true });
                            ctx.drawImage(customHtmlImg, 0, 0);
                            const imageData = ctx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
                            const data = imageData.data;
                            let top = 0, bottom = tempCanvas.height, left = 0, right = tempCanvas.width;
                            outer1: for (let y = 0; y < tempCanvas.height; y++) {
                                for (let x = 0; x < tempCanvas.width; x++) {
                                    if (data[(y * tempCanvas.width + x) * 4 + 3] !== 0) { top = y; break outer1; }
                                }
                            }
                            outer2: for (let y = tempCanvas.height - 1; y >= 0; y--) {
                                for (let x = 0; x < tempCanvas.width; x++) {
                                    if (data[(y * tempCanvas.width + x) * 4 + 3] !== 0) { bottom = y + 1; break outer2; }
                                }
                            }
                            outer3: for (let x = 0; x < tempCanvas.width; x++) {
                                for (let y = 0; y < tempCanvas.height; y++) {
                                    if (data[(y * tempCanvas.width + x) * 4 + 3] !== 0) { left = x; break outer3; }
                                }
                            }
                            outer4: for (let x = tempCanvas.width - 1; x >= 0; x--) {
                                for (let y = 0; y < tempCanvas.height; y++) {
                                    if (data[(y * tempCanvas.width + x) * 4 + 3] !== 0) { right = x + 1; break outer4; }
                                }
                            }
                            let trimW = right - left; let trimH = bottom - top;
                            if (trimW <= 0 || trimH <= 0) { trimW = 1; trimH = 1; left = 0; top = 0; }
                            const trimCanvas = document.createElement('canvas');
                            trimCanvas.width = trimW; trimCanvas.height = trimH;
                            trimCanvas.getContext('2d').putImageData(ctx.getImageData(left, top, trimW, trimH), 0, 0);
                            
                            const croppedImg = new Image();
                            croppedImg.onload = function() {
                                liveEmojiImgObj = new fabric.Image(croppedImg, {
                                    left: origX, top: origY,
                                    originX: 'left', originY: 'top',
                                    isTemp: true, selectable: false, evented: false,
                                    isEmoji: true,
                                    hasBorders: true, hasControls: true,
                                    borderColor: '#3b82f6', borderScaleFactor: 2,
                                    objectCaching: false
                                });
                                liveEmojiImgObj.scaleToWidth(10);
                                canvas.add(liveEmojiImgObj);
                                liveEmojiImgObj.setCoords();
                                canvas.requestRenderAll();
                                if (!isDrawing) {
                                    liveEmojiImgObj.set({ selectable: true, evented: true, isTemp: false });
                                    liveEmojiImgObj.setCoords();
                                    liveEmojiImgObj = null;
                                    updateObjectSelectability();
                                    canvas.requestRenderAll();
                                    saveHistory(); deactivateActiveTool();
                                }
                            };
                            croppedImg.src = trimCanvas.toDataURL();
                        };
                        customHtmlImg.src = selectedEmojiUrl;
                        return;
                    }
                    
                    // 캔버스를 이용해 이모티콘을 이미지로 렌더링 (가장 완벽하고 타이트한 픽셀 단위 외곽선)
                    const tempCanvas = document.createElement('canvas');
                    const tCtx = tempCanvas.getContext('2d');
                    const renderSize = 128; // 고해상도 렌더링 기준 크기
                    tCtx.font = `${renderSize}px "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif`;
                    const metrics = tCtx.measureText(selectedEmoji);
                    
                    let w = Math.ceil(metrics.actualBoundingBoxRight + metrics.actualBoundingBoxLeft);
                    if (isNaN(w) || w <= 0) w = Math.ceil(metrics.width) || renderSize;
                    
                    let h = Math.ceil(metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent);
                    if (isNaN(h) || h <= 0) h = renderSize;
                    
                    tempCanvas.width = w;
                    tempCanvas.height = h;
                    tCtx.font = `${renderSize}px "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif`;
                    tCtx.textBaseline = 'alphabetic';
                    
                    const drawX = metrics.actualBoundingBoxLeft || 0;
                    const drawY = metrics.actualBoundingBoxAscent || (renderSize * 0.8);
                    tCtx.fillText(selectedEmoji, drawX, drawY);
                    
                    const emojiDataUrl = tempCanvas.toDataURL('image/png');
                    const emojiHtmlImg = new Image();
                    emojiHtmlImg.onload = function() {
                        liveEmojiImgObj = new fabric.Image(emojiHtmlImg, {
                            left: origX,
                            top: origY,
                            originX: 'left',
                            originY: 'top',
                            selectable: false,
                            evented: false,
                            isTemp: true,
                            isEmoji: true,
                            baseFontSize: renderSize, // 편집 시 기준 크기
                            scaleX: scaledSize / renderSize,
                            scaleY: scaledSize / renderSize,
                            hasBorders: true,
                            hasControls: true,
                            borderColor: '#3b82f6',
                            borderScaleFactor: 2,
                            objectCaching: false
                        });
                        canvas.add(liveEmojiImgObj);
                        liveEmojiImgObj.setCoords();
                        canvas.requestRenderAll();
                        
                        // 비동기 이미지 로드 중 마우스가 이미 올라간 경우(드래그 없이 클릭만) 즉시 확정
                        if (!isDrawing) {
                            liveEmojiImgObj.set({ selectable: true, evented: true, isTemp: false });
                            liveEmojiImgObj.setCoords();
                            liveEmojiImgObj = null;
                            updateObjectSelectability();
                            canvas.requestRenderAll();
                            saveHistory(); deactivateActiveTool();
                        }
                    };
                    emojiHtmlImg.src = emojiDataUrl;
                } else if (activeTool === 'image') {
                    if (!uploadedImageSrc) return customAlert("이미지 파일을 먼저 선택해주세요.");
                    fabric.Image.fromURL(uploadedImageSrc, img => {
                        const frame = imageInsertData.frame;
                        img.set({ cropX: imageInsertData.sx, cropY: imageInsertData.sy, width: imageInsertData.sw, height: imageInsertData.sh });
                        
                        if (frame === 'circle' || frame === 'ellipse') {
                            img.set({ clipPath: new fabric.Ellipse({ originX: 'center', originY: 'center', rx: imageInsertData.sw/2, ry: imageInsertData.sh/2 }) });
                        }
                        img.set({ originX: 'left', originY: 'top', left: origX, top: origY, scaleX: 0.01, scaleY: 0.01, selectable: false, isTemp: true, isMediaImage: true, frameType: frame });
                        liveEmojiImgObj = img;
                        canvas.add(liveEmojiImgObj);
                    });
                } else if (activeTool === 'shape') {
                    const weight = parseInt(document.getElementById('shape_weight').value);
                    const fColor = getFillOpacity(); 
                    const isDashed = document.getElementById('chk_dashed') && document.getElementById('chk_dashed').checked;
                    const dashArr = isDashed ? [weight * 3, weight * 3] : null;

                    if (shapeType === 'rect') { 
                        currentShape = new fabric.Rect({ left: origX, top: origY, fill: fColor, stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, strokeLineJoin: 'miter', isTemp: true }); canvas.add(currentShape); 
                    } else if (shapeType === 'ellipse') { 
                        currentShape = new fabric.Ellipse({ left: origX, top: origY, originX: 'center', originY: 'center', fill: fColor, stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, isTemp: true }); canvas.add(currentShape); 
                    } else if (shapeType === 'rhombus') {
                        currentShape = new fabric.Polygon([
                            {x: 0, y: 0}, {x: 1, y: 0}, {x: 1, y: 1}, {x: 0, y: 1}
                        ], { left: origX, top: origY, fill: fColor, stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, strokeLineJoin: 'miter', isTemp: true, objectCaching: false });
                        canvas.add(currentShape);
                    }
                }
            }
        });

        let lastEraserTarget = null;
        canvas.on('mouse:move', o => {
            if (!activeTool && !isDrawing && !multiClickDrawing) return;
            if (activeTool === 'crop') { document.getElementById('guide_x').style.top = o.e.clientY + 'px'; document.getElementById('guide_y').style.left = o.e.clientX + 'px'; }

            // 지우개 애니메이션 연동 처리 (부드러운 최적화)
            if (activeTool === 'eraser') {
                const target = canvas.findTarget(o.e, false);

                if (target && target.evented) {
                    if (!isEraserFatState) { updateEraserCursor(true); isEraserFatState = true; }
                    // 마우스 누른 채 이동 시 지우기
                    if (isDrawing) {
                        if (lastEraserTarget && lastEraserTarget !== target) {
                            lastEraserTarget.set('opacity', 1);
                        }
                        canvas.remove(target);
                        lastEraserTarget = null;
                        saveHistory();
                        canvas.requestRenderAll();
                    } else if (lastEraserTarget !== target) {
                        if (lastEraserTarget) lastEraserTarget.set('opacity', 1);
                        target.set('opacity', 0.4);
                        lastEraserTarget = target;
                        canvas.requestRenderAll();
                    }
                } else {
                    if (isEraserFatState) { updateEraserCursor(false); isEraserFatState = false; }
                    if (lastEraserTarget) {
                        lastEraserTarget.set('opacity', 1);
                        lastEraserTarget = null;
                        canvas.requestRenderAll();
                    }
                }
            }

            const pointer = canvas.getPointer(o.e);

            if (activeTool === 'pen' && isDrawing && currentShape && document.querySelector('input[name="pen_mode"]:checked').value === 'straight') {
                let endX = pointer.x; let endY = pointer.y;
                
                let angleDeg = Math.atan2(endY - origY, endX - origX) * 180 / Math.PI;
                let normAngle = (angleDeg + 360) % 360;
                
                const snapTolerance = 2;
                if (Math.abs(normAngle - 0) <= snapTolerance || Math.abs(normAngle - 360) <= snapTolerance) { endY = origY; } 
                else if (Math.abs(normAngle - 90) <= snapTolerance) { endX = origX; } 
                else if (Math.abs(normAngle - 180) <= snapTolerance) { endY = origY; } 
                else if (Math.abs(normAngle - 270) <= snapTolerance) { endX = origX; }
                
                const weight = parseInt(document.getElementById('pen_weight').value) || 5;
                const isDashed = document.getElementById('pen_dashed').checked;
                const dashArr = isDashed ? [weight * 3, weight * 3] : null;

                canvas.remove(currentShape);
                currentShape = new fabric.Path(`M ${origX} ${origY} L ${endX} ${endY}`, {
                    fill: 'transparent', stroke: penCurrentColor, strokeWidth: weight,
                    strokeDashArray: dashArr, strokeLineCap: 'round', strokeLineJoin: 'round',
                    selectable: false, isTemp: true, objectCaching: false
                });
                canvas.add(currentShape);
                canvas.requestRenderAll();
                return;
            }

            if(multiClickDrawing) {
                floatingTooltip.style.left = o.e.clientX + 'px';
                floatingTooltip.style.top = o.e.clientY + 'px';
                
                let snapX = pointer.x; let snapY = pointer.y;
                if (clickPoints.length > 2) {
                    const dist = Math.hypot(pointer.x - clickPoints[0].x, pointer.y - clickPoints[0].y);
                    if (dist < 15) { snapX = clickPoints[0].x; snapY = clickPoints[0].y; }
                }

                clickPoints[clickPoints.length - 1] = {x: snapX, y: snapY};
                const lineRadio = document.querySelector('input[name="line_type"]:checked');
                
                const weight = parseInt(document.getElementById('shape_weight').value);
                const isDashed = document.getElementById('chk_dashed') && document.getElementById('chk_dashed').checked;
                const dashArr = isDashed ? [weight * 3, weight * 3] : null;
                
                let renderPoints = [...clickPoints];

                if(arrowHead && clickPoints.length > 1) {
                    let p2 = clickPoints[clickPoints.length - 1]; let p1 = clickPoints[clickPoints.length - 2];
                    for(let i = clickPoints.length - 2; i >= 0; i--) {
                        if(Math.hypot(clickPoints[i].x - p2.x, clickPoints[i].y - p2.y) > 3) {
                            p1 = clickPoints[i]; break;
                        }
                    }
                    let angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
                    const sizeMult = sysArrowSize === 'xs' ? 1.5 : sysArrowSize === 's' ? 2 : sysArrowSize === 'l' ? 4 : 3;
                    const w = weight * sizeMult + 8;
                    
                    let pullBack = (sysArrowType === 'stealth') ? w * 0.6 : (sysArrowType === 'open') ? 0 : w;
                    let lineEndX = p2.x - Math.cos(angle) * pullBack;
                    let lineEndY = p2.y - Math.sin(angle) * pullBack;
                    renderPoints[renderPoints.length - 1] = {x: lineEndX, y: lineEndY};

                    canvas.remove(arrowHead);
                    arrowHead = createArrowHead(p2.x, p2.y, angle, sysArrowType, sysArrowSize, strokeColor, weight);
                    canvas.add(arrowHead);
                }

                let newPathStr = (lineRadio.value === 'curve') ? getSmoothCurvePath(renderPoints) : renderPoints.reduce((acc, pt, idx) => acc + (idx===0?'M':'L') + ` ${pt.x} ${pt.y} `, '');

                canvas.remove(currentShape);
                currentShape = new fabric.Path(newPathStr, { fill: 'transparent', stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, strokeLineCap: 'round', strokeLineJoin: 'round', isTemp: true, isArrowBody: true });
                canvas.add(currentShape);

                canvas.requestRenderAll();
                return;
            }

            if (!isDrawing) return;
            
            if (activeTool === 'crop') {
                const box = document.getElementById('selection_box'); box.style.display = 'block';
                box.style.width = Math.abs(capStartX - o.e.clientX) + 'px'; box.style.height = Math.abs(capStartY - o.e.clientY) + 'px';
                box.style.left = Math.min(capStartX, o.e.clientX) + 'px'; box.style.top = Math.min(capStartY, o.e.clientY) + 'px';
            }
            else if (['emoji', 'image'].includes(activeTool) && liveEmojiImgObj) {
                const sizeW = Math.abs(origX - pointer.x);
                const sizeH = Math.abs(origY - pointer.y);
                const size = Math.max(sizeW, sizeH);
                liveEmojiImgObj.set({ left: Math.min(origX, pointer.x), top: Math.min(origY, pointer.y) });
                if (activeTool === 'emoji') {
                    const newSize = Math.max(10, size);
                    if (liveEmojiImgObj.baseFontSize) {
                        const s = newSize / liveEmojiImgObj.baseFontSize;
                        liveEmojiImgObj.set({ scaleX: s, scaleY: s });
                    } else {
                        liveEmojiImgObj.scaleToWidth(newSize);
                    }
                } else if (imageInsertData) {
                    const frame = imageInsertData.frame;
                    const sw = imageInsertData.sw || 1;
                    const sh = imageInsertData.sh || 1;
                    if(frame === 'square' || frame === 'circle') {
                        let scale = Math.max(size / sw, size / sh);
                        liveEmojiImgObj.set({ scaleX: scale, scaleY: scale });
                    } else {
                        liveEmojiImgObj.set({ 
                            scaleX: sizeW > 0 ? sizeW / sw : 0.01, 
                            scaleY: sizeH > 0 ? sizeH / sh : 0.01 
                        });
                    }
                }
                canvas.requestRenderAll();
            }
            else if (['mosaic', 'shape'].includes(activeTool) && currentShape) {
                const shapeType = document.getElementById('shape_type').value;
                const lineRadio = document.querySelector('input[name="line_type"]:checked');
                const isNormalLine = (shapeType === 'line' || shapeType === 'arrow') && lineRadio && lineRadio.value === 'normal';

                if (shapeType === 'rect' || activeTool === 'mosaic') { currentShape.set({ width: Math.abs(origX - pointer.x), height: Math.abs(origY - pointer.y) }); if (origX > pointer.x) currentShape.set({ left: pointer.x }); if (origY > pointer.y) currentShape.set({ top: pointer.y }); } 
                else if (shapeType === 'ellipse') { currentShape.set({ rx: Math.abs(origX - pointer.x) / 2, ry: Math.abs(origY - pointer.y) / 2 }); currentShape.set({ left: (origX + pointer.x) / 2, top: (origY + pointer.y) / 2 }); } 
                else if (shapeType === 'rhombus') { 
                    let minX = Math.min(origX, pointer.x);
                    let maxX = Math.max(origX, pointer.x);
                    let minY = Math.min(origY, pointer.y);
                    let maxY = Math.max(origY, pointer.y);
                    let w = maxX - minX; let h = maxY - minY;
                    if(w > 0 && h > 0) {
                        currentShape.set({
                            left: minX, top: minY, width: w, height: h,
                            points: [{x: w/2, y: 0}, {x: w, y: h/2}, {x: w/2, y: h}, {x: 0, y: h/2}]
                        });
                        currentShape._calcDimensions();
                        currentShape.pathOffset = {x: w/2, y: h/2};
                        currentShape.setCoords();
                    }
                } 
                else if (isNormalLine) { 
                    // 일반 화살표도 곡선/다중 클릭과 100% 동일한 알고리즘을 사용하도록 수학적 위치 갱신 도입
                    let angle = Math.atan2(pointer.y - origY, pointer.x - origX);
                    const weight = parseInt(document.getElementById('shape_weight').value);
                    const sizeMult = sysArrowSize === 'xs' ? 1.5 : sysArrowSize === 's' ? 2 : sysArrowSize === 'l' ? 4 : 3;
                    const w = weight * sizeMult + 8;
                    let pullBack = (shapeType === 'arrow') ? ((sysArrowType === 'stealth') ? w * 0.6 : (sysArrowType === 'open') ? 0 : w) : 0;
                    
                    let endX = pointer.x - Math.cos(angle) * pullBack;
                    let endY = pointer.y - Math.sin(angle) * pullBack;
                    
                    let pathStr = `M ${origX} ${origY} L ${endX} ${endY}`;
                    const isDashed = document.getElementById('chk_dashed') && document.getElementById('chk_dashed').checked;
                    const dashArr = isDashed ? [weight * 3, weight * 3] : null;

                    canvas.remove(currentShape);
                    currentShape = new fabric.Path(pathStr, { fill: 'transparent', stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, strokeLineCap: 'round', strokeLineJoin: 'round', isTemp: true, isArrowBody: true }); 
                    canvas.add(currentShape);

                    if (shapeType === 'arrow' && arrowHead) { 
                        canvas.remove(arrowHead);
                        arrowHead = createArrowHead(pointer.x, pointer.y, angle, sysArrowType, sysArrowSize, strokeColor, weight);
                        canvas.add(arrowHead);
                    } 
                }
                canvas.requestRenderAll();
            }
        });

        canvas.on('mouse:up', async o => {
            if (o.target) { o.target.__selectedThisClick = false; o.target.__shapeJustSelected = false; }

            if(multiClickDrawing) return; 
            if(activeTool === 'text' && currentShape) { currentShape.isTemp = false; updateObjectSelectability(); saveHistory(); deactivateActiveTool(); currentShape = null; }
            
            if (activeTool === 'eraser' && isDrawing) { isDrawing = false; return; }
            
            if (!isDrawing) return;
            isDrawing = false;
            
            // 자르기 도구는 엣지 드래그 오버레이로 처리됨 (mouse:up에서 제외)
            if (activeTool === 'crop') { isDrawing = false; return; }

            if (activeTool === 'pen' && currentShape && document.querySelector('input[name="pen_mode"]:checked').value === 'straight') {
                currentShape.setCoords();
                currentShape.set({ selectable: true, isTemp: false });
                currentShape = null;
                updateObjectSelectability();
                canvas.requestRenderAll(); saveHistory(); deactivateActiveTool();
                return;
            }

            if (activeTool === 'mosaic' && currentShape) {
                let mLeft = Math.floor(currentShape.left); 
                let mTop = Math.floor(currentShape.top);
                let mWidth = Math.floor(currentShape.width); 
                let mHeight = Math.floor(currentShape.height);
                
                canvas.remove(currentShape); currentShape = null;

                if (mLeft < 0) { mWidth += mLeft; mLeft = 0; }
                if (mTop < 0) { mHeight += mTop; mTop = 0; }
                if (mLeft + mWidth > canvas.width) mWidth = canvas.width - mLeft;
                if (mTop + mHeight > canvas.height) mHeight = canvas.height - mTop;

                if (mWidth > 10 && mHeight > 10) {
                    let oldClip = canvas.clipPath;
                    canvas.clipPath = null;
                    canvas.renderAll(); 

                    const cropData = canvas.toDataURL({ left: mLeft, top: mTop, width: mWidth, height: mHeight, format: 'png', multiplier: 1 });
                    
                    canvas.clipPath = oldClip;
                    canvas.renderAll();
                    
                    const imgObj = new Image();
                    imgObj.onload = function() {
                        const tempCanvas = document.createElement('canvas');
                        tempCanvas.width = mWidth; tempCanvas.height = mHeight;
                        const tempCtx = tempCanvas.getContext('2d', { willReadFrequently: true });
                        
                        tempCtx.drawImage(imgObj, 0, 0, mWidth, mHeight);
                        const imgData = tempCtx.getImageData(0, 0, mWidth, mHeight).data;

                        const outCanvas = document.createElement('canvas');
                        outCanvas.width = mWidth; outCanvas.height = mHeight;
                        const outCtx = outCanvas.getContext('2d');

                        let k = Math.max(1, window.sysMosaicPx);
                        if (k > 20) k = 20;

                        const cols = Math.ceil(mWidth / k);
                        const rows = Math.ceil(mHeight / k);
                        let cellColors = new Array(rows).fill(0).map(() => new Array(cols).fill(null));

                        for (let r = 0; r < rows; r++) {
                            for (let c = 0; c < cols; c++) {
                                let cx = Math.min(c * k + Math.floor(k / 2), mWidth - 1);
                                let cy = Math.min(r * k + Math.floor(k / 2), mHeight - 1);
                                let idx = (cy * mWidth + cx) * 4;
                                cellColors[r][c] = {
                                    r: imgData[idx], g: imgData[idx+1], b: imgData[idx+2], a: imgData[idx+3]
                                };
                            }
                        }

                        let finalColors = new Array(rows).fill(0).map(() => new Array(cols).fill(null));
                        let processed = new Array(rows).fill(0).map(() => new Array(cols).fill(false));

                        let setIndex = 0;
                        for (let r = 0; r < rows - 1; r += 2) {
                            for (let c = 0; c < cols - 1; c += 2) {
                                let type = setIndex % 4;
                                let p00 = cellColors[r][c], p01 = cellColors[r][c+1];
                                let p10 = cellColors[r+1][c], p11 = cellColors[r+1][c+1];

                                if (type === 0 || type === 2) {
                                    finalColors[r][c] = p11; finalColors[r+1][c+1] = p00;
                                    finalColors[r][c+1] = p10; finalColors[r+1][c] = p01;
                                } else if (type === 1) { 
                                    finalColors[r][c+1] = p00; finalColors[r+1][c+1] = p01;
                                    finalColors[r+1][c] = p11; finalColors[r][c] = p10;
                                } else if (type === 3) { 
                                    finalColors[r+1][c] = p00; finalColors[r+1][c+1] = p10;
                                    finalColors[r][c+1] = p11; finalColors[r][c] = p01;
                                }
                                processed[r][c] = processed[r][c+1] = processed[r+1][c] = processed[r+1][c+1] = true;
                                setIndex++;
                            }
                        }

                        let flatCells = [];
                        for (let r = 0; r < rows; r++) {
                            for (let c = 0; c < cols; c++) {
                                if (!processed[r][c]) flatCells.push({r, c});
                            }
                        }
                        for (let i = 0; i < flatCells.length - 1; i += 2) {
                            let p1 = flatCells[i]; let p2 = flatCells[i+1];
                            finalColors[p1.r][p1.c] = cellColors[p2.r][p2.c];
                            finalColors[p2.r][p2.c] = cellColors[p1.r][p1.c];
                        }
                        if (flatCells.length % 2 !== 0) {
                            let p = flatCells[flatCells.length - 1];
                            finalColors[p.r][p.c] = cellColors[p.r][p.c];
                        }

                        for (let r = 0; r < rows; r++) {
                            for (let c = 0; c < cols; c++) {
                                let col = finalColors[r][c];
                                if (col.a > 0) { 
                                    outCtx.fillStyle = `rgba(${col.r},${col.g},${col.b},${col.a/255})`;
                                    outCtx.fillRect(c * k, r * k, k, k); 
                                }
                            }
                        }

                        fabric.Image.fromURL(outCanvas.toDataURL('image/png'), (patchImg) => {
                            patchImg.set({ left: mLeft, top: mTop, selectable: true, isMosaic: true });
                            canvas.add(patchImg); canvas.bringToFront(patchImg);
                            updateObjectSelectability();
                            canvas.requestRenderAll(); saveHistory();
                        });
                    };
                    imgObj.src = cropData;
                }
            }
            else if (['emoji', 'image'].includes(activeTool) && liveEmojiImgObj) { 
                liveEmojiImgObj.set({ selectable: true, evented: true, isTemp: false }); 
                liveEmojiImgObj.setCoords();
                liveEmojiImgObj = null; 
                updateObjectSelectability();
                canvas.requestRenderAll(); saveHistory(); 
            } 
            else if (activeTool === 'shape' && currentShape) {
                const shapeType = document.getElementById('shape_type').value;
                const lineRadio = document.querySelector('input[name="line_type"]:checked');
                const isNormalLine = (shapeType === 'line' || shapeType === 'arrow') && lineRadio && lineRadio.value === 'normal';

                if (currentShape) {
                    if (arrowHead) {
                        canvas.remove(currentShape, arrowHead);
                        const group = new fabric.Group([currentShape, arrowHead], {selectable: true});
                        canvas.add(group);
                    } else {
                        currentShape.setCoords();
                        currentShape.set({ selectable: true, isTemp: false });
                    }
                }
                currentShape = null; arrowHead = null;
                updateObjectSelectability();
                canvas.requestRenderAll(); saveHistory(); deactivateActiveTool();
            }
        });

        // 커스텀 버튼 그룹 이벤트 바인딩
        document.querySelectorAll('.custom-select-group').forEach(group => {
            const hiddenInput = document.getElementById(group.id.replace('_group', ''));
            group.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', () => {
                    group.querySelectorAll('button').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    hiddenInput.value = btn.getAttribute('data-val');
                    hiddenInput.dispatchEvent(new Event('change'));
                });
            });
        });
        // ==========================================
        // ★ 자르기 네 변 조절 시스템
        // ==========================================
        let cropL = 0, cropT = 0, cropR = 0, cropB = 0;
        let cropAdjusted = false;

        function updateCropOverlayUI() {
            const cw = canvas.width, ch = canvas.height;
            const ov = document.getElementById('crop_edge_overlay');
            ov.style.width = cw + 'px';
            ov.style.height = ch + 'px';

            // 마스크 (외부 어둡게)
            document.getElementById('crop_mask_top').style.cssText    = `left:0;right:0;top:0;height:${cropT}px;`;
            document.getElementById('crop_mask_bottom').style.cssText = `left:0;right:0;bottom:0;height:${ch-cropB}px;`;
            document.getElementById('crop_mask_left').style.cssText   = `left:0;top:${cropT}px;width:${cropL}px;height:${cropB-cropT}px;`;
            document.getElementById('crop_mask_right').style.cssText  = `right:0;top:${cropT}px;width:${cw-cropR}px;height:${cropB-cropT}px;`;

            // 엣지 라인
            document.getElementById('crop_line_top').style.cssText    = `left:${cropL}px;right:${cw-cropR}px;top:${cropT-2}px;`;
            document.getElementById('crop_line_bottom').style.cssText = `left:${cropL}px;right:${cw-cropR}px;top:${cropB-2}px;`;
            document.getElementById('crop_line_left').style.cssText   = `left:${cropL-2}px;top:${cropT}px;bottom:${ch-cropB}px;`;
            document.getElementById('crop_line_right').style.cssText  = `left:${cropR-2}px;top:${cropT}px;bottom:${ch-cropB}px;`;

            // 코너 핸들
            const c = 6; // 오프셋
            document.getElementById('crop_corner_tl').style.cssText = `left:${cropL-c}px;top:${cropT-c}px;`;
            document.getElementById('crop_corner_tr').style.cssText = `left:${cropR-c}px;top:${cropT-c}px;`;
            document.getElementById('crop_corner_bl').style.cssText = `left:${cropL-c}px;top:${cropB-c}px;`;
            document.getElementById('crop_corner_br').style.cssText = `left:${cropR-c}px;top:${cropB-c}px;`;

            // 자르기 버튼 활성화
            const btn = document.getElementById('btn_do_crop');
            if (cropAdjusted) { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = 'pointer'; }
            else              { btn.disabled = true;  btn.style.opacity = '0.4'; btn.style.cursor = 'default'; }
        }

        function initCropOverlay() {
            if (!hasActiveCanvas) return;
            cropL = 0; cropT = 0; cropR = canvas.width; cropB = canvas.height;
            cropAdjusted = false;
            const ov = document.getElementById('crop_edge_overlay');
            ov.style.display = 'block';
            updateCropOverlayUI();
        }

        function hideCropOverlay() {
            document.getElementById('crop_edge_overlay').style.display = 'none';
            cropAdjusted = false;
            const btn = document.getElementById('btn_do_crop');
            btn.disabled = true; btn.style.opacity = '0.4';
        }

        // ── 엣지 드래그 이벤트 ──────────────────────────────────────
        (function setupCropDrag() {
            const edges = [
                { id: 'crop_line_top',    axis: 'y', target: 'T' },
                { id: 'crop_line_bottom', axis: 'y', target: 'B' },
                { id: 'crop_line_left',   axis: 'x', target: 'L' },
                { id: 'crop_line_right',  axis: 'x', target: 'R' },
            ];
            edges.forEach(({ id, axis, target }) => {
                const el = document.getElementById(id);
                let dragging = false, startClient = 0, startVal = 0;

                el.addEventListener('mousedown', e => {
                    e.stopPropagation(); e.preventDefault();
                    dragging = true;
                    startClient = axis === 'y' ? e.clientY : e.clientX;
                    startVal = target === 'T' ? cropT : target === 'B' ? cropB :
                               target === 'L' ? cropL : cropR;
                    document.body.style.userSelect = 'none';
                });
                window.addEventListener('mousemove', e => {
                    if (!dragging) return;
                    const delta = (axis === 'y' ? e.clientY - startClient : e.clientX - startClient) / currentZoom;
                    const MIN_SIZE = 20;
                    const cw = canvas.width, ch = canvas.height;
                    if (target === 'T')      cropT = Math.max(0,       Math.min(cropB - MIN_SIZE, Math.round(startVal + delta)));
                    else if (target === 'B') cropB = Math.min(ch,      Math.max(cropT + MIN_SIZE, Math.round(startVal + delta)));
                    else if (target === 'L') cropL = Math.max(0,       Math.min(cropR - MIN_SIZE, Math.round(startVal + delta)));
                    else                     cropR = Math.min(cw,      Math.max(cropL + MIN_SIZE, Math.round(startVal + delta)));
                    cropAdjusted = true;
                    updateCropOverlayUI();
                });
                window.addEventListener('mouseup', () => {
                    if (dragging) { dragging = false; document.body.style.userSelect = ''; }
                });
            });
        })();

        // ── 자르기 실행 버튼 ──────────────────────────────────────────
        document.getElementById('btn_do_crop').addEventListener('click', performEdgeCrop);

        async function performEdgeCrop() {
            if (!hasActiveCanvas || !cropAdjusted) return;
            const cLeft = cropL, cTop = cropT;
            const newW = cropR - cropL, newH = cropB - cropT;
            if (newW < 20 || newH < 20) return;

            hideCropOverlay();
            canvas.discardActiveObject();

            // 1. 개체 목록 복사 후 캔버스에서 일시 제거 (배경만 남김)
            const objects = canvas.getObjects().slice();
            objects.forEach(o => canvas.remove(o));
            canvas.renderAll();

            // 2. 배경 영역만 toDataURL로 추출
            const bgData = canvas.toDataURL({
                left: cLeft, top: cTop, width: newW, height: newH,
                format: 'png', multiplier: 1
            });

            // 3. 배경 이미지 교체
            fabric.Image.fromURL(bgData, (img) => {
                isHistoryAction = true;
                img.set({ originX: 'left', originY: 'top', left: 0, top: 0, scaleX: 1, scaleY: 1 });
                canvas.setWidth(newW);
                canvas.setHeight(newH);
                canvas.setBackgroundImage(img, () => {
                    // 4. 개체 위치 보정 후 재추가 (경계 걸치거나 내부 개체만)
                    objects.forEach(o => {
                        o.set({ left: o.left - cLeft, top: o.top - cTop });
                        o.setCoords();
                        const br = o.getBoundingRect();
                        // 완전히 바깥인 개체만 제외, 나머지 모두 유지
                        if (br.left + br.width > 0 && br.left < newW &&
                            br.top + br.height > 0 && br.top < newH) {
                            o.set({ selectable: true, evented: true });
                            canvas.add(o);
                        }
                    });
                    panX = 0; panY = 0;
                    applyFitZoom(); applyCanvasClipping();
                    canvas.renderAll();
                    isHistoryAction = false; saveHistory();
                    // 자르기 도구 비활성화
                    document.getElementById('btn_tool_crop').click();
                });
            });
        }

    