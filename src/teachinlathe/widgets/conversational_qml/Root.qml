import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root
    objectName: "root"
    anchors.fill: parent

    // Navigation state (stack of { url, params })
    property var history: []
    property string currentSource: ""
    property var _currentParams: ({})     // last applied params for currentSource
    property var _pendingParams: null     // params to apply after Loader creates its item

    function canGoBack() { return history.length > 0 }

    // Push a new screen (store the current screen state in history)
    function loadScreen(url, params) {
        if (currentSource !== "" && loader.item) {
            history.push({ url: currentSource, params: _currentParams })
        }
        currentSource = url
        _currentParams = params || {}
        _pendingParams = _currentParams
        loader.setSource(url) // Qt5-safe; we apply params in onLoaded
    }

    // Replace current screen without adding another history entry.
    function replaceScreen(url, params) {
        currentSource = url
        _currentParams = params || {}
        _pendingParams = _currentParams
        loader.setSource(url)
    }

    // Pop last screen and restore its params
    function goBack() {
        if (!canGoBack())
            return
        var state = history.pop()
        currentSource = state.url
        _currentParams = state.params || {}
        _pendingParams = _currentParams
        loader.setSource(state.url)
    }

    Loader {
        id: loader
        objectName: "loader"
        anchors.fill: parent

        onLoaded: {
            if (!item)
                return

            // 1) Apply captured params (from loadScreen/goBack)
            if (root._pendingParams) {
                for (var k in root._pendingParams) {
                    try { item[k] = root._pendingParams[k] } catch (e) { console.warn(e) }
                }
            }

            // 2) Auto-inject global programsModel if screen exposes it but it's missing
            try {
                if (item.hasOwnProperty("programsModel") && !item.programsModel && typeof programsModel !== "undefined") {
                    item.programsModel = programsModel
                    // keep it in current params for future pushes
                    root._currentParams.programsModel = programsModel
                }
            } catch (e) { console.warn(e) }

            // 3) Back visibility based on history (if the screen supports it)
            if (item.hasOwnProperty("showBack")) {
                item.showBack = root.canGoBack()
                root._currentParams.showBack = item.showBack
            }
        }
    }
}
