#include "VstHost.h"
#include <juce_audio_basics/juce_audio_basics.h>
#include <juce_core/juce_core.h>
#include <stdexcept>

VstHost::VstHost() {
    formatManager = std::make_unique<juce::AudioPluginFormatManager>();
    formatManager->addDefaultFormats();
    pluginList = std::make_unique<juce::KnownPluginList>();
}

VstHost::~VstHost() = default;

// ── Load plugin ───────────────────────────────────────────────────────────────

std::unique_ptr<juce::AudioPluginInstance>
VstHost::loadPlugin(const std::string& vst_path, double sampleRate, int blockSize) {
    juce::OwnedArray<juce::PluginDescription> descs;
    juce::VST3PluginFormat fmt;

    fmt.findAllTypesForFile(descs, juce::String(vst_path));
    if (descs.isEmpty())
        throw std::runtime_error("No VST3 plugin found at: " + vst_path);

    juce::String err;
    auto instance = formatManager->createPluginInstance(
        *descs[0], sampleRate, blockSize, err);

    if (!instance)
        throw std::runtime_error("Failed to load plugin: " + err.toStdString());

    instance->prepareToPlay(sampleRate, blockSize);
    instance->setPlayConfigDetails(0, 2, sampleRate, blockSize);
    return instance;
}

// ── Load MIDI ─────────────────────────────────────────────────────────────────

juce::MidiBuffer VstHost::loadMidi(const std::string& midi_path,
                                    double bpm, int sampleRate) {
    juce::MidiBuffer buffer;
    juce::File file(juce::String(midi_path));

    if (!file.existsAsFile())
        return buffer;

    juce::FileInputStream stream(file);
    juce::MidiFile midiFile;
    if (!midiFile.readFrom(stream))
        return buffer;

    midiFile.convertTimestampTicksToSeconds();
    double secPerBeat = 60.0 / bpm;

    for (int track = 0; track < midiFile.getNumTracks(); ++track) {
        const juce::MidiMessageSequence* seq = midiFile.getTrack(track);
        for (int i = 0; i < seq->getNumEvents(); ++i) {
            const auto& event = seq->getEventPointer(i)->message;
            int sample = static_cast<int>(event.getTimeStamp() * sampleRate);
            buffer.addEvent(event, sample);
        }
    }
    return buffer;
}

// ── Write WAV ─────────────────────────────────────────────────────────────────

void VstHost::writeWav(const juce::AudioBuffer<float>& audioBuffer,
                        int sampleRate, const std::string& output_path) {
    juce::File outFile(juce::String(output_path));
    outFile.getParentDirectory().createDirectory();

    juce::WavAudioFormat wavFormat;
    auto stream = std::unique_ptr<juce::FileOutputStream>(outFile.createOutputStream());
    if (!stream) throw std::runtime_error("Cannot create output file: " + output_path);

    auto writer = std::unique_ptr<juce::AudioFormatWriter>(
        wavFormat.createWriterFor(stream.get(), sampleRate, 2, 24, {}, 0));
    if (!writer) throw std::runtime_error("Cannot create WAV writer");

    stream.release();  // writer owns the stream
    writer->writeFromAudioSampleBuffer(audioBuffer, 0, audioBuffer.getNumSamples());
}

// ── Render ────────────────────────────────────────────────────────────────────

RenderResult VstHost::render(const RenderRequest& req) {
    RenderResult result;
    try {
        auto plugin = loadPlugin(req.vst_path, req.sample_rate, req.buffer_size);
        auto midi   = loadMidi(req.midi_path, req.bpm, req.sample_rate);

        int totalSamples = req.sample_rate * req.duration_secs;
        juce::AudioBuffer<float> output(2, totalSamples);
        output.clear();

        int pos = 0;
        while (pos < totalSamples) {
            int block = std::min(req.buffer_size, totalSamples - pos);
            juce::AudioBuffer<float> blockBuf(2, block);
            blockBuf.clear();

            juce::MidiBuffer blockMidi;
            for (auto it = midi.begin(); it != midi.end(); ++it) {
                int s = (*it).samplePosition - pos;
                if (s >= 0 && s < block)
                    blockMidi.addEvent((*it).getMessage(), s);
            }

            plugin->processBlock(blockBuf, blockMidi);

            for (int ch = 0; ch < 2; ++ch)
                output.copyFrom(ch, pos, blockBuf, ch, 0, block);

            pos += block;
        }

        writeWav(output, req.sample_rate, req.output_path);

        result.success       = true;
        result.output_path   = req.output_path;
        result.duration_secs = static_cast<double>(totalSamples) / req.sample_rate;
    }
    catch (const std::exception& e) {
        result.success = false;
        result.error   = e.what();
    }
    return result;
}
