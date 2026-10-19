import 'package:flutter/material.dart';

import '../api.dart';
import '../labels.dart';
import '../profile.dart';
import 'brand_list_screen.dart';
import 'measurements_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.api, required this.store});

  final ApiClient api;
  final ProfileStore store;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Profile? _profile;
  Map<String, dynamic>? _meta;
  String? _apiError;

  @override
  void initState() {
    super.initState();
    _loadProfile();
    _loadMeta();
  }

  Future<void> _loadProfile() async {
    final profile = await widget.store.load();
    if (!mounted) {
      return;
    }
    setState(() => _profile = profile);
  }

  Future<void> _loadMeta() async {
    try {
      final meta = await widget.api.meta();
      if (!mounted) {
        return;
      }
      setState(() {
        _meta = meta;
        _apiError = null;
      });
    } on Exception catch (e) {
      if (!mounted) {
        return;
      }
      setState(() => _apiError = e.toString());
    }
  }

  Future<void> _editMeasurements() async {
    final profile = _profile;
    if (profile == null) {
      return;
    }
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => MeasurementsScreen(api: widget.api, store: widget.store, profile: profile),
    ));
    await _loadProfile();
  }

  Future<void> _openBrands() async {
    final profile = _profile;
    if (profile == null) {
      return;
    }
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => BrandListScreen(api: widget.api, store: widget.store, profile: profile),
    ));
    await _loadProfile();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final profile = _profile;
    return Scaffold(
      appBar: AppBar(title: const Text('WhatSize')),
      body: profile == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text('Tvoje velikost v každé značce', style: theme.textTheme.headlineSmall),
                const SizedBox(height: 8),
                Text(
                  'Zadej pár měr a appka ti řekne, jakou velikost si vzít u konkrétní značky.',
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: 16),
                _ProfileCard(profile: profile, onEdit: _editMeasurements),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _openBrands,
                  icon: const Icon(Icons.storefront),
                  label: const Text('Najít velikost ve značce'),
                ),
                const SizedBox(height: 24),
                _DataNotice(meta: _meta, error: _apiError, onRetry: _loadMeta),
              ],
            ),
    );
  }
}

class _ProfileCard extends StatelessWidget {
  const _ProfileCard({required this.profile, required this.onEdit});

  final Profile profile;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final entries = [
      for (final f in fieldsFor(profile.gender))
        if (profile.measurements[f.key] != null)
          '${f.label}: ${_fmt(profile.measurements[f.key]!)} ${f.unit}',
    ];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.straighten, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Text('Moje míry', style: theme.textTheme.titleMedium),
                const Spacer(),
                Text(profile.gender == 'M' ? 'Muž' : 'Žena'),
              ],
            ),
            const SizedBox(height: 12),
            if (entries.isEmpty)
              const Text('Zatím žádné míry. Stačí začít jednou — appka se sama doptá na další.')
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [for (final e in entries) Chip(label: Text(e))],
              ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onEdit,
              icon: const Icon(Icons.edit),
              label: Text(entries.isEmpty ? 'Zadat míry' : 'Upravit míry'),
            ),
          ],
        ),
      ),
    );
  }
}

class _DataNotice extends StatelessWidget {
  const _DataNotice({required this.meta, required this.error, required this.onRetry});

  final Map<String, dynamic>? meta;
  final String? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final style = theme.textTheme.bodySmall;
    if (error != null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Spojení se serverem se nepodařilo: $error', style: style),
          TextButton(onPressed: onRetry, child: const Text('Zkusit znovu')),
        ],
      );
    }
    final m = meta;
    if (m == null) {
      return Text('Připojuji se k serveru… (napoprvé to může trvat až minutu)', style: style);
    }
    return Text(
      'Testovací verze · ${m['brands']} značek · data ${m['data_version']}. '
      '${m['data_note'] ?? ''}',
      style: style,
    );
  }
}

String _fmt(double v) => v == v.roundToDouble() ? v.toStringAsFixed(0) : v.toString();
