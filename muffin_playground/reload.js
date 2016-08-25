(function() {
  var ws = new WebSocket('ws://' + document.location.host + '/__reload__/')
  ws.onmessage = function(evt) {
    if (evt.data === 'reload') {
      console.log('Reloading...')
      ws.close()
      document.location.reload()
    }
  }
})()
