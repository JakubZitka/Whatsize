import 'package:flutter/material.dart';

import '../api.dart';
import '../labels.dart';
import '../profile.dart';

/// Precise measurement entry (PRD FR-1.2). Every field is optional (FR-1.3):
/// the brand screen asks only for what a category actually needs.
class MeasurementsScreen extends StatefulWidget {
  const MeasurementsScreen({
    super.key,
    required this.api,
    required this.store,
    required this.profile,
  });

  final ApiClient api;
  final ProfileStore store;
  final Profile profile;

  @override
  State<MeasurementsScreen> createState() => _MeasurementsScreenState();
}

class _MeasurementsScreenState extends State<MeasurementsScreen> {
  late String _gender;
  final Map<String, TextEditingController> _controllers = {};
  Map<String, String> _errors = {};
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _gender = widget.profile.gender;
    for (final key in {...womenFields.map((f) => f.key), ...menFields.map((f) => f.key)}) {
      final value = widget.profile.measurements[key];
      _controllers[key] = TextEditingController(text: value == null ? '' : _fmt(value));
    }
  }

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Map<String, double>? _parse() {
    final values = <String, double>{};
    final errors = <String, String>{};
    for (final f in fieldsFor(_gender)) {
      final text = _controllers[f.key]!.text.trim().replaceAll(',', '.');
      if (text.isEmpty) {
        continue;
      }
      final value = double.tryParse(text);
      if (value == null) {
        errors[f.key] = 'Zadej číslo.';
      } else {
        values[f.key] = value;
      }
    }
    setState(() => _errors = errors);
    return errors.isEmpty ? values : null;
  }

  Future<void> _save() async {
    final values = _parse();
    if (values == null) {
      return;
    }
    final candidate = Profile(gender: _gender, measurements: values);
    setState(() => _saving = true);
    Map<String, dynamic>? result;
    try {
      result = await widget.api.validate(candidate);
    } on Exception {
      result = null; // Offline: save anyway, the server validates again on use.
    }
    if (!mounted) {
      return;
    }
    setState(() => _saving = false);
    if (result != null) {
      final errors = <String, String>{
        for (final e in (result['errors'] as List).cast<Map>())
          e['field'] as String: e['message'] as String,
      };
      if (errors.isNotEmpty) {
        setState(() => _errors = errors);
        return;
      }
      final warnings = (result['warnings'] as List).cast<Map>();
      if (warnings.isNotEmpty) {
        final ok = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Neobvyklé hodnoty'),
            content: Text([for (final w in warnings) w['message']].join('\n')),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Opravit'),
              ),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('Je to správně'),
              ),
            ],
          ),
        );
        if (ok != true) {
          return;
        }
      }
    }
    widget.profile
      ..gender = _gender
      ..measurements.clear()
      ..measurements.addAll(values);
    await widget.store.save(widget.profile);
    if (!mounted) {
      return;
    }
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Moje míry')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'W', label: Text('Žena'), icon: Icon(Icons.woman)),
              ButtonSegment(value: 'M', label: Text('Muž'), icon: Icon(Icons.man)),
            ],
            selected: {_gender},
            onSelectionChanged: (s) => setState(() {
              _gender = s.first;
              _errors = {};
            }),
          ),
          const SizedBox(height: 16),
          const Text('Vyplň, co znáš. Nic není povinné — appka se doptá jen na to, co '
              'u dané kategorie potřebuje.'),
          const SizedBox(height: 16),
          for (final f in fieldsFor(_gender)) ...[
            TextField(
              controller: _controllers[f.key],
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: f.label,
                suffixText: f.unit,
                helperText: f.help,
                helperMaxLines: 3,
                errorText: _errors[f.key],
                errorMaxLines: 3,
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
          ],
          FilledButton(
            onPressed: _saving ? null : _save,
            child: Text(_saving ? 'Ukládám…' : 'Uložit'),
          ),
        ],
      ),
    );
  }
}

String _fmt(double v) => v == v.roundToDouble() ? v.toStringAsFixed(0) : v.toString();
