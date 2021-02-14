// NOTE: all dates in this code are ISO formatted date strings (YYYY-MM-DD) in local time.
//      in the few cases where a javascript date object is needed it is called dateObj

// The name of the server with the data for this page
// const dataServer = 'http://inpakrovmais:8080'
const dataServer = 'https://inpakrovmais.nps.doi.net:8443'
// const dataServer = '//localhost:8080'

// Return bytes as human readable quantity
// Credit: https://stackoverflow.com/a/14919494
function humanFileSize (bytes, si) {
  const thresh = si ? 1000 : 1024
  if (Math.abs(bytes) < thresh) {
    return bytes + ' Bytes'
  }
  const units = si
    ? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
  let u = -1
  do {
    bytes /= thresh
    ++u
  } while (Math.abs(bytes) >= thresh && u < units.length - 1)
  return bytes.toFixed(1) + ' ' + units[u]
}

// rounds a number to a specified number of decimal digits
// credit: http://www.jacklmoore.com/notes/rounding-in-javascript/
function round (value, decimals) {
  return Number(Math.round(value + 'e' + decimals) + 'e-' + decimals)
}

// Adds or updates the parameter in a query string
// credit: https://stackoverflow.com/a/11654596
function UpdateQueryString (key, value, url) {
  if (!url) url = window.location.href
  const re = new RegExp('([?&])' + key + '=.*?(&|#|$)(.*)', 'gi')

  if (re.test(url)) {
    if (typeof value !== 'undefined' && value !== null) {
      return url.replace(re, '$1' + key + '=' + value + '$2$3')
    } else {
      const hash = url.split('#')
      url = hash[0].replace(re, '$1$3').replace(/(&|\?)$/, '')
      if (typeof hash[1] !== 'undefined' && hash[1] !== null) {
        url += '#' + hash[1]
      }
      return url
    }
  } else {
    if (typeof value !== 'undefined' && value !== null) {
      const separator = url.indexOf('?') !== -1 ? '&' : '?'
      const hash = url.split('#')
      url = hash[0] + separator + key + '=' + value
      if (typeof hash[1] !== 'undefined' && hash[1] !== null) {
        url += '#' + hash[1]
      }
      return url
    } else return url
  }
}

// Left pad a number to two digits with a zero
function pad2 (n) {
  return n < 10 ? '0' + n : n
}

// Produce a short ISO formatted date from a date object
function isoDateFormat (dateObj) {
  return (
    dateObj.getFullYear() +
    '-' +
    pad2(dateObj.getMonth() + 1) +
    '-' +
    pad2(dateObj.getDate())
  )
}

// Returns a Date() obj if valid, false otherwise
// It is flexible in that zero padding is not required, and month/day default to Jan/1
function validIsoDate (str) {
  if (!str) {
    return false
  }
  try {
    const parts = str.split('-')
    const year = parts[0]
    const month = (parts[1] || 1) - 1
    const day = parts[2] || 1
    const dateObj = new Date(year, month, day)
    if (dateObj instanceof Date && !isNaN(dateObj)) {
      return dateObj
    } else {
      return false
    }
  } catch (error) {
    return false
  }
}

// Produce a date object from a short ISO formatted date
// It is flexible in that zero padding is not required, and month/day default to Jan/1
// an invalid date will result in today's date being returned
function dateFromIso (str) {
  return validIsoDate(str) || new Date()
}

// Validate a user provided iso date string
// if date is null then the current date will be assumed
// if date is outside range, then it will be clipped to the range
// Range is open, i.e. minDate and maxDate are allowed, if null then no limit
function validateDate (date, minDate, maxDate) {
  const dateObj = dateFromIso(date)
  const newDate = isoDateFormat(dateObj)
  if (minDate && newDate < minDate) {
    return minDate
  }
  if (maxDate && maxDate < newDate) {
    return maxDate
  }
  return newDate
}

// Returns an ISO format date for yesterday (presumably the last time robo ran)
function getYesterday () {
  const dateObj = new Date()
  dateObj.setDate(dateObj.getDate() - 1) // yesterday
  return isoDateFormat(dateObj)
}

// generic request to get JSON data from data service
function getJSON (url, callback, errorback) {
  const xhr = new XMLHttpRequest()
  xhr.open('GET', url, true)
  xhr.responseType = 'json'
  xhr.onload = function () {
    if (this.readyState === this.DONE) {
      if (this.status === 200) {
        if (this.response !== null) {
          callback(this.response)
        } else {
          errorback('Bad JSON object returned from Server')
        }
      } else {
        errorback(this.statusText)
      }
    }
  }
  xhr.onerror = function (e) {
    errorback('Error fetching data for report. Check if service is running.')
  }
  xhr.send()
}

// Success callback for adding summary data to the web page
function postSummary (data) {
  document.getElementById('summary_wait').hidden = true
  if (Object.keys(data).length === 0 && data.constructor === Object) {
    document.getElementById('summary_fail').hidden = false
    return
  }
  const date = data.summary_date
  const countStarts = data.count_start
  const countUnfinished = data.count_unfinished
  const countErrors = data.count_with_errors
  const hasChanges = data.has_changes
  const hasParseErrors = data.has_parse_errors
  const hasIssues = countErrors > 0 || countUnfinished > 0

  const countEle = document.getElementById('count_total_parks')
  if (countStarts === 0) {
    countEle.textContent = 'no parks'
  } else if (countStarts === 1) {
    countEle.textContent = '1 park'
  } else if (countStarts > 1) {
    countEle.textContent = countStarts + ' parks'
  }

  var ele = document.getElementById('summary_incomplete_count')
  if (countUnfinished === 1) {
    ele.textContent = '1 park'
  } else {
    ele.textContent = countUnfinished + ' parks'
  }
  document.getElementById('summary_incomplete').hidden = countUnfinished === 0

  ele = document.getElementById('summary_errors_count')
  if (countErrors === 1) {
    ele.textContent = '1 park'
  } else {
    ele.textContent = countErrors + ' parks'
  }
  document.getElementById('summary_errors').hidden = countErrors === 0

  if (hasIssues) {
    document.getElementById('summary_issues').hidden = false
    document.getElementById('summary_no_issues').hidden = true
    if (countErrors === 0) {
      document
        .getElementById('summary_card')
        .classList.replace('nominal', 'warning')
    } else {
      document
        .getElementById('summary_card')
        .classList.replace('nominal', 'error')
    }
  } else {
    document.getElementById('summary_issues').hidden = true
    document.getElementById('summary_no_issues').hidden = false
    document
      .getElementById('summary_card')
      .classList.replace('error', 'nominal')
    document
      .getElementById('summary_card')
      .classList.replace('warning', 'nominal')
  }

  document.getElementById('error_card').hidden = !hasParseErrors

  // Change: 2020-08-18 always show the change log (even if there are no changes)
  document.getElementById('changelog_link').href = 'PDS_ChangeLog.html#' + date
  if (hasChanges) {
    document.getElementById('summary_no_changes').hidden = true
  } else {
    document.getElementById('summary_no_changes').hidden = false
  }
  document.getElementById('summary_card').hidden = false
}

// Success callback for adding park details to the web page
function postParkDetails (data) {
  if (data.length === 1) {
    document.getElementById('park_cards').innerHTML = '' // hiding doesn't work due to display: flex in card-container class
    document.getElementById('park_wait').hidden = true
    document.getElementById('park_fail').hidden = false
    return
  }
  // ["park","date","finished","countErrors","files_copied","filesRemoved","filesScanned","timeCopying","timeScanning","bytesCopied"]
  // Ignore the first row (header), assume there are no more then 20 parks
  let html = ''
  data.slice(1, 20).forEach(row => {
    const park = row[0]
    const date = row[1]
    const bytesCopied = row[9]
    const sizeCopied = humanFileSize(bytesCopied, true)
    const timeCopying = row[7]
    const copySpeed = round(bytesCopied / timeCopying / 1000.0, 1)
    let copyText =
      timeCopying === 0
        ? 'Nothing copied.'
        : `${sizeCopied} in ${timeCopying} seconds (${copySpeed} kB/sec)`
    copyText = timeCopying == null ? 'Unknown' : copyText
    const filesScanned = row[6]
    const timeScanning = row[8]
    const scanSpeed = round(filesScanned / timeScanning, 1)
    const filesRemoved = row[5]
    const finished = row[2]
    const countErrors = row[3]
    const status =
      countErrors === 0 ? (finished === 1 ? 'nominal' : 'warning') : 'error'
    const errorStr = countErrors === 0 ? '' : `${countErrors} Errors.`
    const finishStr =
      finished === 1 ? '' : 'Robocopy did not finish (no timing data).'
    let issues = 'No Issues.'
    if (errorStr === '' && finishStr !== '') {
      issues = finishStr
    } else if (errorStr !== '' && finishStr === '') {
      issues = errorStr
    } else if (errorStr !== '' && finishStr !== '') {
      issues = errorStr + ' ' + finishStr
    }
    const scanText =
      filesScanned == null
        ? 'Unknown'
        : `${filesScanned} files in ${timeScanning} seconds (${scanSpeed} files/sec)`
    const removedText =
      filesRemoved == null ? 'Unknown' : `${filesRemoved} files`
    const cardStr = `
      <div class='card ${status} inline'>
        <h3>${park}</h3>
        <dl>
        <dt>Copied</dt>
        <dd>${copyText}</dd>
        <dt>Scanned</dt>
        <dd>${scanText}</dd>
        <dt>Removed</dt>
        <dd>${removedText}</dd>
        <dt>Issues</dt>
        <dd>${issues}</dd>
        </dl>
        <a href='${dataServer}/logfile?park=${park}&date=${date}'>Log file</a>
      </div>
    `
    html += cardStr
  })
  document.getElementById('park_cards').innerHTML = html
  document.getElementById('park_wait').hidden = true
  document.getElementById('park_cards').hidden = false
}

// Error callback for adding summary error to the web page
function summaryFailed (message) {
  const ele = document.getElementById('summary_fail')
  if (message === 'Service Unavailable') {
    const message2 = 'Check to make sure the python service is running.'
    ele.textContent = message + '. ' + message2
  } else {
    ele.textContent = message
  }
  ele.hidden = false
  document.getElementById('summary_wait').hidden = true
}

// Error callback for adding park details error to the web page
function parksFailed (message) {
  const ele = document.getElementById('park_fail')
  ele.textContent = message
  ele.hidden = false
  document.getElementById('park_wait').hidden = true
}

// Update the state of the date text and the next/previous date buttons
function fixDateButtonState (date) {
  const previousButton = document.getElementById('previous_date')
  const nextButton = document.getElementById('next_date')

  // Use a javascript date object because it makes date math much easier
  //   getDate and setDate get/set the day of the month
  //   setDate will roll up/down a month/year as needed if the new day is out of range
  let dateObj = dateFromIso(date)
  dateObj.setDate(dateObj.getDate() + 1) // Add one day to the date
  nextButton.dataset.destination = isoDateFormat(dateObj)
  dateObj = dateFromIso(date)
  dateObj.setDate(dateObj.getDate() - 1) // Subtract one day to the date
  previousButton.dataset.destination = isoDateFormat(dateObj)

  previousButton.hidden = date <= previousButton.dataset.limit
  nextButton.hidden = nextButton.dataset.limit <= date
}

function plot2bars (x, l1, y1, l2, y2, title) {
  const trace1 = {
    x: x,
    y: y1,
    name: l1,
    type: 'bar'
  }

  const trace2 = {
    x: x,
    y: y2,
    name: l2,
    type: 'bar'
  }
  const layout = {
    barmode: 'group',
    title: title
  }
  Plotly.newPlot('graph_div', [trace1, trace2], layout)
}

function plotline (x, l1, y1, title) {
  const trace1 = {
    x: x,
    y: y1,
    name: l1,
    type: 'scatter',
    mode: 'lines'
  }
  const layout = {
    title: title
  }
  Plotly.newPlot('graph_div', [trace1], layout)
}

function unpack (rows, key) {
  return rows.map(function (row) {
    return row[key]
  })
}

function plot1 (data) {
  if (data.length < 2) {
    getPlotDataFail('No plot data for this date.')
    return
  }
  document.getElementById('graph_wait').hidden = true
  document.getElementById('graph_div').hidden = false
  plot2bars(
    unpack(data, 0), // park
    'Copy Speed (kB/s)',
    unpack(data, 2), // copySpeed
    'Scan Speed (files/s)',
    unpack(data, 1), // scanSpeed
    'Park Speed Comparison (single night)'
  )
}

function plot2 (data) {
  document.getElementById('graph_wait').hidden = true
  document.getElementById('graph_div').hidden = false
  document.getElementById('date_pickers').hidden = false
  plot2bars(
    unpack(data, 0), // park
    'Scan Speed (files/s)',
    unpack(data, 1), // avg scan speed
    '# of days',
    unpack(data, 2), // # of days
    'Average Scan Speed'
  )
}

function plot3 (data) {
  document.getElementById('graph_wait').hidden = true
  document.getElementById('graph_div').hidden = false
  document.getElementById('date_pickers').hidden = false
  plot2bars(
    unpack(data, 0), // park
    'Copy Speed (kB/s)',
    unpack(data, 1), // avg copy speed
    '# of days',
    unpack(data, 2), // # of days
    'Average Copy Speed'
  )
}

function plot4 (data) {
  document.getElementById('graph_wait').hidden = true
  document.getElementById('graph_div').hidden = false
  document.getElementById('park_picker').hidden = false
  const park = data[0][0]
  const title = 'Scan Speed (files/second) for ' + park
  plotline(
    // data 0 has the park name
    unpack(data, 1),
    'Scan Speed (files/s)',
    unpack(data, 2),
    title
  )
}

function plot5 (data) {
  document.getElementById('graph_wait').hidden = true
  document.getElementById('graph_div').hidden = false
  document.getElementById('park_picker').hidden = false
  const park = data[0][0]
  const title = 'Copy Speed (kB/sec) for ' + park
  plotline(
    // data 0 has the park name
    unpack(data, 1),
    'Copy Speed (kB/s)',
    unpack(data, 3),
    title
  )
}

function getPlotDataFail (err) {
  const ele = document.getElementById('graph_fail')
  ele.hidden = false
  if (err) {
    ele.textContent = err
  }
  document.getElementById('graph_wait').hidden = true
}

// ===========
// DOM Events
// ===========

// eslint-disable-next-line no-unused-vars
function nextDate () {
  const newDate = document.getElementById('next_date').dataset.destination
  const url = UpdateQueryString('date', newDate)
  window.history.pushState({ date: newDate }, '', url)
  setupPage(newDate)
}

// eslint-disable-next-line no-unused-vars
function previousDate () {
  const newDate = document.getElementById('previous_date').dataset.destination
  const url = UpdateQueryString('date', newDate)
  window.history.pushState({ date: newDate }, '', url)
  setupPage(newDate)
}

function prepForNewGraph () {
  const graph = document.getElementById('graph_div')
  graph.hidden = true
  document.getElementById('graph_fail').hidden = true
  document.getElementById('park_picker').hidden = true
  document.getElementById('date_pickers').hidden = true
  document.getElementById('graph_wait').hidden = false
  while (graph.firstChild) {
    graph.removeChild(graph.firstChild)
  }
}

// eslint-disable-next-line no-unused-vars
function plotParks1 () {
  prepForNewGraph()
  const date = document.getElementById('page_date').textContent
  const url = dataServer + '/plot1?date=' + date
  getJSON(url, plot1, getPlotDataFail)
}

// eslint-disable-next-line no-unused-vars
function plotParks2 () {
  prepForNewGraph()
  const element = document.getElementById('date_pickers')
  element.removeEventListener('change', refreshPlot3)
  element.addEventListener('change', refreshPlot2)
  refreshPlot2()
}

function refreshPlot2 () {
  if (!document.getElementById('graph_fail').hidden) {
    prepForNewGraph()
  }
  const date1 = document.getElementById('start_date').value
  const date2 = document.getElementById('end_date').value
  // ignore bad (usually inprogress) dates in the pickers
  if (!date1 || !date2) {
    return
  }
  const url = dataServer + '/scanavg?start=' + date1 + '&end=' + date2
  getJSON(url, plot2, getPlotDataFail)
}

// eslint-disable-next-line no-unused-vars
function plotParks3 () {
  prepForNewGraph()
  const element = document.getElementById('date_pickers')
  element.removeEventListener('change', refreshPlot2)
  element.addEventListener('change', refreshPlot3)
  refreshPlot3()
}

function refreshPlot3 () {
  if (!document.getElementById('graph_fail').hidden) {
    prepForNewGraph()
  }
  const date1 = document.getElementById('start_date').value
  const date2 = document.getElementById('end_date').value
  // ignore bad (usually inprogress) dates in the pickers
  if (!date1 || !date2) {
    return
  }
  const url = dataServer + '/copyavg?start=' + date1 + '&end=' + date2
  getJSON(url, plot3, getPlotDataFail)
}

// eslint-disable-next-line no-unused-vars
function plotParks4 () {
  prepForNewGraph()
  const element = document.getElementById('park_select')
  element.removeEventListener('change', refreshPlot5)
  element.addEventListener('change', refreshPlot4)
  refreshPlot4()
}

function refreshPlot4 () {
  if (!document.getElementById('graph_fail').hidden) {
    prepForNewGraph()
  }
  const date = document.getElementById('page_date').textContent
  const park = document.getElementById('park_select').value
  const url = dataServer + '/speed?park=' + park + '&start=2018-01-22&end=' + date
  getJSON(url, plot4, getPlotDataFail)
}

// eslint-disable-next-line no-unused-vars
function plotParks5 () {
  prepForNewGraph()
  const element = document.getElementById('park_select')
  element.removeEventListener('change', refreshPlot4)
  element.addEventListener('change', refreshPlot5)
  refreshPlot5()
}

function refreshPlot5 () {
  if (!document.getElementById('graph_fail').hidden) {
    prepForNewGraph()
  }
  const date = document.getElementById('page_date').textContent
  const park = document.getElementById('park_select').value
  const url = dataServer + '/speed?park=' + park + '&start=2018-01-22&end=' + date
  getJSON(url, plot5, getPlotDataFail)
}

// Get data from the services and update the page
function setupPage (date) {
  document.getElementById('page_date').textContent = date
  fixDateButtonState(date)
  const query = '?date=' + date
  document.getElementById('summary_wait').hidden = false
  document.getElementById('summary_card').hidden = true
  document.getElementById('summary_fail').hidden = true
  getJSON(dataServer + '/summary' + query, postSummary, summaryFailed)
  document.getElementById('park_wait').hidden = false
  document.getElementById('park_cards').hidden = true
  document.getElementById('park_fail').hidden = true
  getJSON(dataServer + '/parks' + query, postParkDetails, parksFailed)
}

// Get data from the services and update the page
function setupSite () {
  const lastNight = getYesterday()
  const firstNight = '2018-01-22'
  const startDatePicker = document.getElementById('start_date')
  startDatePicker.min = firstNight
  startDatePicker.max = lastNight
  startDatePicker.value = firstNight
  const endDatePicker = document.getElementById('end_date')
  endDatePicker.min = firstNight
  endDatePicker.max = lastNight
  endDatePicker.value = lastNight
  document.getElementById('previous_date').dataset.limit = firstNight
  document.getElementById('next_date').dataset.limit = lastNight
  const params = new URLSearchParams(document.location.search.substring(1))
  const date = validateDate(params.get('date'), firstNight, lastNight)
  window.history.replaceState({ date: date }, '', document.location)
  setupPage(date)
}

setupSite()
window.onpopstate = function (event) {
  if (event.state.date) {
    setupPage(event.state.date)
  }
}
