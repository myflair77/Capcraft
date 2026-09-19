/* Keep Chromium's last changed frame flowing through the embedded Qt surface.
 * Only the compositor runs during this bounded pulse; Fabric is not re-rendered.
 */
window.installPresentationRefresh = function () {
    if (window.capcraftPresentationRefresh) return;
    let animation = null;
    let timer = null;
    const refresh = () => {
        if (timer !== null || document.hidden) return;
        timer = setTimeout(() => {
            timer = null;
            if (animation) animation.cancel();
            animation = document.documentElement.animate(
                [{opacity:1}, {opacity:0.9999}, {opacity:1}],
                {duration:180, iterations:1}
            );
            animation.onfinish = () => { animation = null; };
        }, 0);
    };
    window.capcraftPresentationRefresh = refresh;
    for (const event of ['pointerup', 'keyup', 'input', 'change', 'wheel']) {
        document.addEventListener(event, refresh, {capture:true, passive:true});
    }
    canvas.on('after:render', e => {
        if (e.ctx === canvas.contextContainer) refresh();
    });
};
