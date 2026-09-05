<?php
/**
 * Plugin Name: VAD — block outgoing mail (non-production)
 * Description: Hard stop on every outgoing email. Installed on staging and
 *              development only. File-based on purpose: FluentSMTP's
 *              simulate_emails setting lives in the database, so a refresh
 *              from production overwrites it. This survives that.
 *
 * Installed by: make block-mail env=<name>, which substitutes
 *               __PRODUCTION_HOST__ with environments.production.url from
 *               site.yml so this file is identical across projects.
 * Do not edit on the server — edit scripts/remote/ in the repo.
 */

/**
 * Exact host match, never a substring: staging is commonly a SUBDOMAIN of
 * production, and strpos( 'https://staging.example.com', 'example.com' )
 * matches — which silently disabled this block on staging and let real mail
 * out. An empty or unparseable WP_HOME is not production either, so the guard
 * fails closed and the block stays active.
 */
function ntdst_mail_block_is_production( $home, $production_host ) {
    $host = strtolower( (string) parse_url( (string) $home, PHP_URL_HOST ) );

    return '' !== $host && $host === strtolower( (string) $production_host );
}

// Self-disable if this ever lands on production by accident.
add_action( 'muplugins_loaded', function () {
    $home = defined( 'WP_HOME' ) ? WP_HOME : '';
    if ( ntdst_mail_block_is_production( $home, '__PRODUCTION_HOST__' ) ) {
        return; // production — do nothing
    }

    // Short-circuit wp_mail() entirely. Returning non-null makes WordPress
    // skip its own sending and report success, so nothing downstream errors.
    add_filter( 'pre_wp_mail', function ( $null, $atts ) {
        $to = is_array( $atts['to'] ?? '' ) ? implode( ',', $atts['to'] ) : (string) ( $atts['to'] ?? '' );
        error_log( sprintf( '[ntdst-mail-block] suppressed mail to %s — %s', $to, $atts['subject'] ?? '(no subject)' ) );
        return true;
    }, PHP_INT_MAX, 2 );

    // FluentCRM and FluentSMTP can bypass wp_mail on some paths.
    add_filter( 'fluentmail_will_log_email', '__return_false', PHP_INT_MAX );
    add_filter( 'fluent_crm/disable_email_sending', '__return_true', PHP_INT_MAX );
}, 0 );
