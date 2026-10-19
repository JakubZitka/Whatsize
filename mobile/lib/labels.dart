/// Measurement fields and display labels (Czech UI).
class MeasurementField {
  const MeasurementField(this.key, this.label, this.unit, this.help);

  final String key;
  final String label;
  final String unit;
  final String help;
}

const _stature = MeasurementField(
  'stature_cm',
  'Výška',
  'cm',
  'Bez bot, zády ke zdi, od podlahy po temeno.',
);
const _foot = MeasurementField(
  'foot_length_mm',
  'Délka chodidla',
  'mm',
  'Ve stoje, pata u zdi, po špičku nejdelšího prstu. Změř obě nohy, ber delší.',
);
const _waist = MeasurementField(
  'waist_cm',
  'Obvod pasu',
  'cm',
  'V nejužším místě pasu, uvolněně, metr vodorovně.',
);
const _hip = MeasurementField(
  'hip_cm',
  'Obvod boků',
  'cm',
  'V nejširším místě sedu, nohy u sebe.',
);

const womenFields = [
  _stature,
  MeasurementField(
    'bust_chest_cm',
    'Obvod přes prsa',
    'cm',
    'Přes nejplnější místo. Metr VOLNĚ — jen leží, nestahuje.',
  ),
  MeasurementField(
    'underbust_cm',
    'Obvod pod prsy',
    'cm',
    'Těsně pod prsy. Metr PEVNĚ — utáhni, normálně vydechni. Potřeba jen pro podprsenky.',
  ),
  _waist,
  _hip,
  _foot,
];

const menFields = [
  _stature,
  MeasurementField(
    'bust_chest_cm',
    'Obvod hrudníku',
    'cm',
    'Pod pažemi přes nejširší místo hrudníku, metr vodorovně.',
  ),
  MeasurementField(
    'neck_cm',
    'Obvod krku',
    'cm',
    'V úrovni ohryzku, prst pod metrem. Potřeba jen pro košile.',
  ),
  _waist,
  _hip,
  _foot,
];

List<MeasurementField> fieldsFor(String gender) => gender == 'M' ? menFields : womenFields;

String fieldLabel(String key, String gender) {
  for (final f in fieldsFor(gender)) {
    if (f.key == key) {
      return f.label;
    }
  }
  return key;
}

String fitName(String? code) => const {
      'regular': 'Regular',
      'slim': 'Slim',
      'skinny': 'Skinny',
      'relaxed': 'Relaxed',
      'oversized': 'Oversized',
      'petite': 'Petite',
      'tall': 'Tall',
      'curvy': 'Curvy',
      'athletic': 'Athletic',
      'plus': 'Plus',
      'maternity': 'Těhotenské',
    }[code] ??
    (code ?? '');

/// Short prefix shown before a size label, e.g. "EU 38" or "US W 8.5".
String systemPrefix(String? system) => const {
      'EU_DE': 'EU',
      'EU_FR': 'EU (FR)',
      'IT': 'IT',
      'UK': 'UK',
      'US': 'US',
      'AU': 'AU',
      'NECK_CM': 'Límec',
      'NECK_IN': 'Límec (in)',
      'KIDS_HEIGHT': 'Výška',
      'BRA_EU': 'EU',
      'BRA_FR': 'FR',
      'BRA_IT': 'IT',
      'BRA_UK': 'UK',
      'BRA_US': 'US',
      'SHOE_EU': 'EU',
      'SHOE_UK': 'UK',
      'SHOE_US_M': 'US M',
      'SHOE_US_W': 'US W',
    }[system] ??
    '';

const preferenceLabels = {
  'a_bit_tight': 'Těsněji',
  'perfect': 'Akorát',
  'a_bit_loose': 'Volněji',
};
