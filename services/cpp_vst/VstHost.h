#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_audio_formats/juce_audio_formats.h>
#include <string>
#include <memory>

struct RenderRequest {
    std::string midi_path;
    std::string vst_path;
    std::string output_path;
    int         sample_rate   = 44100;
    int         buffer_size   = 512;
    double      bpm           = 120.0;
    int         duration_secs = 30;
};

struct RenderResult {
    bool        success = false;
    std::string output_path;
    std::string error;
    double      duration_secs = 0.0;
};

class VstHost {
public:
    VstHost();
    ~VstHost();

    RenderResult render(const RenderRequest& req);

private:
    std::unique_ptr<juce::AudioPluginFormatManager> formatManager;
    std::unique_ptr<juce::KnownPluginList>          pluginList;

    std::unique_ptr<juce::AudioPluginInstance> loadPlugin(
        const std::string& vst_path, double sampleRate, int blockSize);

    juce::MidiBuffer loadMidi(const std::string& midi_path, double bpm, int sampleRate);

    void writeWav(const juce::AudioBuffer<float>& buffer,
                  int sampleRate, const std::string& output_path);
};
