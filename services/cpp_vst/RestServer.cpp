#include "VstHost.h"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <iostream>
#include <string>

using json = nlohmann::json;

// ── Entry point ───────────────────────────────────────────────────────────────

int main() {
    juce::ScopedJuceInitialiser_GUI juceInit;  // headless JUCE init
    VstHost host;

    httplib::Server svr;

    // ── /health ───────────────────────────────────────────────────────────────
    svr.Get("/health", [](const httplib::Request&, httplib::Response& res) {
        json body = {{"status", "ok"}, {"port", 8003}};
        res.set_content(body.dump(), "application/json");
    });

    // ── /render ───────────────────────────────────────────────────────────────
    svr.Post("/render", [&host](const httplib::Request& req, httplib::Response& res) {
        try {
            auto body = json::parse(req.body);

            RenderRequest rr;
            rr.midi_path    = body.at("midi_path").get<std::string>();
            rr.vst_path     = body.at("vst_path").get<std::string>();
            rr.output_path  = body.at("output_path").get<std::string>();
            rr.sample_rate  = body.value("sample_rate",   44100);
            rr.buffer_size  = body.value("buffer_size",   512);
            rr.bpm          = body.value("bpm",           120.0);
            rr.duration_secs = body.value("duration_secs", 30);

            auto result = host.render(rr);

            json resp;
            resp["success"]       = result.success;
            resp["output_path"]   = result.output_path;
            resp["duration_secs"] = result.duration_secs;
            if (!result.error.empty())
                resp["error"] = result.error;

            int code = result.success ? 200 : 500;
            res.set_content(resp.dump(), "application/json");
            res.status = code;
        }
        catch (const std::exception& e) {
            json err = {{"success", false}, {"error", e.what()}};
            res.set_content(err.dump(), "application/json");
            res.status = 400;
        }
    });

    // ── /plugins/scan ─────────────────────────────────────────────────────────
    svr.Post("/plugins/scan", [](const httplib::Request& req, httplib::Response& res) {
        auto body = json::parse(req.body);
        std::string scan_path = body.value("path", "C:/Program Files/Common Files/VST3");

        juce::AudioPluginFormatManager mgr;
        mgr.addDefaultFormats();
        juce::KnownPluginList list;
        juce::VST3PluginFormat fmt;

        juce::OwnedArray<juce::PluginDescription> descs;
        fmt.findAllTypesForFile(descs, juce::String(scan_path));

        json plugins = json::array();
        for (auto* d : descs) {
            plugins.push_back({
                {"name",          d->name.toStdString()},
                {"manufacturer",  d->manufacturerName.toStdString()},
                {"file_or_id",    d->fileOrIdentifier.toStdString()},
            });
        }
        json resp = {{"path", scan_path}, {"count", plugins.size()}, {"plugins", plugins}};
        res.set_content(resp.dump(), "application/json");
    });

    std::cout << "[VstHost] Listening on 0.0.0.0:8003\n";
    svr.listen("0.0.0.0", 8003);
    return 0;
}
