(function() {
  var ws = new WebSocket('ws://' + document.location.host + '/__debug__/')
  ws.onmessage = function(evt) {
    if (evt.data === 'reload') {
      console.log('Reloading...')
      ws.close()
      document.location.reload()
    } else {
      document.body.innerHTML = ''
      var div = document.createElement('div')
      div.style = 'font-family: monospace'
      div.innerText = evt.data
      document.body.appendChild(div)
    }
  }
})()
