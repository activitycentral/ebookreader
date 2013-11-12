    var parentElement;
    var actualChild;
    var actualWord;
    var words;
    var originalNode = null;
    var modifiedNode = null;

    function trim(s) { 
      s =  ( s || '' ).replace( /^\s+|\s+$/g, '' ); 
      return s.replace(/[\n\r\t]/g,' ');
    }


    function init() {
        parentElement = document.getElementsByTagName("body")[0];
        actualChild = new Array();
        actualWord = 0;
        actualChild.push(0);
    }

    function highLightNextWordInt() {
        var nodeList = parentElement.childNodes;
        ini_posi = actualChild[actualChild.length - 1];
        for (var i=ini_posi; i < nodeList.length; i++) {
            var node = nodeList[i];            
            if ((node.nodeName == "#text") && (trim(node.nodeValue) != '')) {
                node_text =  trim(node.nodeValue);
                words = node_text.split(" ");
                if (actualWord < words.length) {
                    originalNode = document.createTextNode(node.nodeValue);
                    
                    prev_text = '';
                    for (var p1 = 0; p1 < actualWord; p1++) {
                        prev_text = prev_text + words[p1] + " ";
                    }
                    var textNode1 = document.createTextNode(prev_text);
                    var textNode2 = document.createTextNode(words[actualWord]+" ");
                    post_text = '';
                    for (var p2 = actualWord + 1; p2 < words.length; p2++) {
                        post_text = post_text + words[p2] + " ";
                    }
                    var textNode3 = document.createTextNode(post_text);
                    var newParagraph = document.createElement('p');
                    var boldNode = document.createElement('b');
                    boldNode.appendChild(textNode2);
                    newParagraph.appendChild(textNode1);    
                    newParagraph.appendChild(boldNode);    
                    newParagraph.appendChild(textNode3);    

                    parentElement.insertBefore(newParagraph, node);
                    parentElement.removeChild(node);
                    modifiedNode = newParagraph;

                    actualWord = actualWord + 1;
                    if (actualWord >=  words.length) {
                        actualChild.pop();
                        actualChild[actualChild.length - 1] = actualChild[actualChild.length - 1] + 2;
                        actualWord = 0;
                        parentElement = parentElement.parentNode;
                    }
                }    
                throw "exit"; 
            } else {
                if (node.childNodes.length > 0) {
                    parentElement = node;
                    actualChild.push(0);
                    actualWord = 0;
                    highLightNextWordInt();
                    actualChild.pop();
                }
            }
        }
        return;
    }


    function highLightNextWord() {
        if (typeof parentElement  == "undefined") {
            init();
        }
        if (originalNode != null) {
            modifiedNode.parentNode.insertBefore(originalNode, modifiedNode);
            modifiedNode.parentNode.removeChild(modifiedNode);
        } 
        try {
            highLightNextWordInt();
        } catch(er) {
        }
    }
