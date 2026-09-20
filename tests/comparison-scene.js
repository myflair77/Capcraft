window.prepareComparisonScene=async function(){
 await prepareRenderingScene();
 // Identical synthetic scene in Chrome and Qt, including a populated sidebar.
 for(let i=0;i<5;i++)pushCurrentToRecent(true);
 document.title='Capcraft — Chrome/Qt comparison (synthetic data)';
};
