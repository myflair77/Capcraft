/* Endpoints are fixed in the target's local coordinate system, not re-snapped. */
(() => {
    function capture(target,point) {
        if(!target.id)target.id='anchor_'+Date.now()+'_'+Math.random().toString(36).slice(2);
        const local=fabric.util.transformPoint(point,fabric.util.invertTransform(target.calcTransformMatrix()));
        return {targetId:target.id,x:local.x/(target.width||1),y:local.y/(target.height||1)};
    }
    function point(target,anchor) {
        return fabric.util.transformPoint({x:anchor.x*(target.width||1),y:anchor.y*(target.height||1)},target.calcTransformMatrix());
    }
    function ensure(line) {
        const pts=line.__capcraftPoints;if(!pts||pts.length<2)return;
        for(const [side,index] of [['start',0],['end',pts.length-1]]) {
            const target=line[side+'LinkedObj'],key=side+'Anchor';
            if(!target){line[key]=null;continue;}
            if(!line[key]||line[key].targetId!==target.id)line[key]=capture(target,pts[index]);
        }
    }
    const original=fabric.Object.prototype.toObject;
    fabric.Object.prototype.toObject=function(properties){return original.call(this,['startAnchor','endAnchor'].concat(properties||[]));};
    window.LineAnchors={capture,point,ensure};
})();
