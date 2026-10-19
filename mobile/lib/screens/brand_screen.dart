import 'package:flutter/material.dart';

import '../api.dart';
import '../labels.dart';
import '../profile.dart';
import 'measurements_screen.dart';

/// The user's size in every category the brand carries (FR-3.1, FR-3.3).
class BrandScreen extends StatefulWidget {
  const BrandScreen({
    super.key,
    required this.api,
    required this.store,
    required this.profile,
    required this.brand,
  });

  final ApiClient api;
  final ProfileStore store;
  final Profile profile;
  final Map<String, dynamic> brand;

  @override
  State<BrandScreen> createState() => _BrandScreenState();
}

class _BrandScreenState extends State<BrandScreen> {
  String _preference = 'perfect';
  late Future<List<Map<String, dynamic>>> _results;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _results = widget.api.brandRecommendations(
      widget.brand['brand_id'] as String,
      widget.profile,
      _preference,
    );
  }

  Future<void> _editMeasurements() async {
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => MeasurementsScreen(
        api: widget.api,
        store: widget.store,
        profile: widget.profile,
      ),
    ));
    if (!mounted) {
      return;
    }
    setState(_load);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.brand['brand_name'] as String)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Jak to máš rád/a?', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: [
              for (final e in preferenceLabels.entries)
                ButtonSegment(value: e.key, label: Text(e.value)),
            ],
            selected: {_preference},
            onSelectionChanged: (s) => setState(() {
              _preference = s.first;
              _load();
            }),
          ),
          const SizedBox(height: 16),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _results,
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return Text('Nepodařilo se načíst velikosti: ${snapshot.error}');
              }
              final results = snapshot.data;
              if (results == null) {
                return const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              if (results.isEmpty) {
                return const Text('Tahle značka pro tebe v našich datech nic nemá.');
              }
              return Column(
                children: [
                  for (final r in results)
                    _ResultCard(
                      result: r,
                      gender: widget.profile.gender,
                      onAddMeasurement: _editMeasurements,
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({
    required this.result,
    required this.gender,
    required this.onAddMeasurement,
  });

  final Map<String, dynamic> result;
  final String gender;
  final VoidCallback onAddMeasurement;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final status = result['status'] as String;
    final title = result['category_name'] as String;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            if (status == 'ok') ..._ok(theme),
            if (status == 'needs_measurement') ...[
              Text(
                'Chybí míra: ${[
                  for (final m in (result['missing'] as List)) fieldLabel(m as String, gender),
                ].join(', ')}',
              ),
              TextButton(onPressed: onAddMeasurement, child: const Text('Doplnit míru')),
            ],
            if (status == 'no_answer') Text(result['explanation'] as String),
          ],
        ),
      ),
    );
  }

  List<Widget> _ok(ThemeData theme) {
    final prefix = systemPrefix(result['size_system'] as String?);
    final label = result['size_label'] as String;
    final runnerUp = result['runner_up'] as String?;
    final confidence = (result['confidence'] as num).toDouble();
    final fit = result['fit_code'] as String?;
    final warnings = (result['warnings'] as List).cast<Map>();
    final notes = (result['notes'] as List).cast<String>();
    return [
      Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            prefix.isEmpty ? label : '$prefix $label',
            style: theme.textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 12),
          if (fit != null && fit != 'regular')
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Chip(label: Text('Střih ${fitName(fit)}')),
            ),
        ],
      ),
      if (runnerUp != null)
        Text('Jsi na hranici — zvaž i $runnerUp.', style: theme.textTheme.bodyMedium),
      const SizedBox(height: 8),
      Row(
        children: [
          Expanded(child: LinearProgressIndicator(value: confidence)),
          const SizedBox(width: 8),
          Text('Jistota ${(confidence * 100).round()} %', style: theme.textTheme.bodySmall),
        ],
      ),
      for (final w in warnings)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.warning_amber, size: 18, color: theme.colorScheme.error),
              const SizedBox(width: 6),
              Expanded(child: Text(w['message'] as String)),
            ],
          ),
        ),
      const SizedBox(height: 8),
      Text(result['explanation'] as String, style: theme.textTheme.bodySmall),
      for (final n in notes)
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(n, style: theme.textTheme.bodySmall),
        ),
    ];
  }
}
