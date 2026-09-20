/* Compatibility entry point. Readback mitigation was too slow and ineffective.
 * Do not force native repaint, animate opacity, or read pixels during editing. */
window.installPresentationRefresh = function () {
    if (window.capcraftPresentationRefresh) return;
    window.capcraftPresentationRefresh = function () {};
};
