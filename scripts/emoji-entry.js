import data from 'emoji-picker-element-data/en/emojibase/data.json';
// Works under Qt's file:// origin without a server or remote fetch.
document.getElementById('ep_main').setAttribute('data-source',
    'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(data)));
import('emoji-picker-element');
